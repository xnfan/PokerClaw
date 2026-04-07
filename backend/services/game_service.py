"""Game service: orchestrates creating/running games, bridges API and engine."""
from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from backend.agent.llm_agent import LLMAgent
from backend.agent.human_agent import HumanAgent

if TYPE_CHECKING:
    from backend.services.hand_lab import ScenarioConfig
from backend.agent.personality import PersonalityProfile, PlayStyle, SkillLevel
from backend.database import get_db, now_iso
from backend.engine.cash_game import CashGame, CashGameConfig
from backend.engine.game_runner import HandResult
from backend.llm.mock_provider import MockLLMProvider
from backend.monitoring.agent_monitor import AgentMonitor
from backend.monitoring.llm_metrics import LLMMetricsCollector
from backend.monitoring.metrics_aggregator import MetricsAggregator


# In-memory registry of active games
_active_games: dict[str, "GameSession"] = {}
_monitor = AgentMonitor()
_aggregator = MetricsAggregator(_monitor)


def get_monitor() -> AgentMonitor:
    return _monitor


def get_aggregator() -> MetricsAggregator:
    return _aggregator


@dataclass
class GameSession:
    session_id: str
    game: CashGame
    status: str = "waiting"  # waiting / pending_start / running / finished
    hand_results: list[dict] = field(default_factory=list)
    on_event: Callable | None = None  # WebSocket broadcast callback
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    _num_hands: int = 10  # store num_hands for deferred start
    lab_config: "ScenarioConfig" | None = None  # NEW: set for Hand Lab sessions
    human_player_id: str | None = None  # NEW: set if human player in game


def create_agent_from_db(agent_id: str) -> LLMAgent:
    """Load agent config from DB and create LLMAgent instance."""
    db = get_db()
    row = db.execute("SELECT * FROM agents WHERE agent_id=?", (agent_id,)).fetchone()
    db.close()
    if not row:
        raise ValueError(f"Agent {agent_id} not found")

    skill = SkillLevel(row["skill_level"])
    style = PlayStyle(row["play_style"])
    personality = PersonalityProfile(skill, style, row["custom_traits"] or "")

    # For MVP, use mock provider; real provider when api_key is set
    if row["llm_provider"] == "anthropic" and row["llm_api_key"]:
        from backend.llm.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider(
            api_key=row["llm_api_key"], model=row["llm_model"]
        )
    else:
        mock_map = {
            "tag": "aggressive", "lag": "aggressive", "rock": "passive",
            "calling_station": "passive", "fish": "random", "maniac": "aggressive",
        }
        # Add delay to simulate LLM thinking and make game watchable
        provider = MockLLMProvider(
            style=mock_map.get(row["play_style"], "random"), delay_ms=1500
        )

    return LLMAgent(
        agent_id=agent_id,
        display_name=row["display_name"],
        personality=personality,
        llm_provider=provider,
        monitor=_monitor,
    )


def create_game(
    agent_ids: list[str],
    small_blind: int = 50,
    big_blind: int = 100,
    buy_in: int = 5000,
    human_player: dict[str, Any] | None = None,
) -> GameSession:
    """Create a new game session with the given agents."""
    config = CashGameConfig(
        small_blind=small_blind, big_blind=big_blind,
        street_delay_ms=1200.0, hand_delay_ms=2000.0,
    )
    game = CashGame(config)
    session_id = game.session_id

    # Add AI agents
    for aid in agent_ids:
        agent = create_agent_from_db(aid)
        game.add_player(aid, agent.display_name, agent, buy_in=buy_in)

    # Add human player if specified
    human_player_id: str | None = None
    if human_player:
        human_id = human_player.get("player_id", f"human_{str(uuid.uuid4())[:8]}")
        human_name = human_player.get("display_name", "Player")
        human_agent = HumanAgent(human_id, human_name)
        game.add_player(human_id, human_name, human_agent, buy_in=buy_in)
        human_player_id = human_id

    session = GameSession(
        session_id=session_id,
        game=game,
        human_player_id=human_player_id,
    )
    _active_games[session_id] = session

    # Persist to DB
    db = get_db()
    db.execute(
        "INSERT INTO game_sessions (session_id, game_type, status, small_blind, big_blind, max_players, created_at) VALUES (?,?,?,?,?,?,?)",
        (session_id, "cash", "waiting", small_blind, big_blind, 9, now_iso()),
    )
    db.commit()
    db.close()
    return session


def start_lab_session(config: "ScenarioConfig", count: int = 1) -> GameSession:
    """Create a Hand Lab session that will stream events via WebSocket."""
    # Lazy import to avoid circular import (hand_lab imports from game_service)
    from backend.services.hand_lab import ScenarioConfig

    # Build name map
    name_map: dict[str, str] = {}
    for ps in config.players:
        name_map[ps.agent_id] = _get_agent_name(ps.agent_id)

    # Create CashGame with pacing delays
    game_config = CashGameConfig(
        small_blind=config.small_blind,
        big_blind=config.big_blind,
        street_delay_ms=1200.0,
        hand_delay_ms=2000.0,
    )
    game = CashGame(game_config)
    session_id = game.session_id

    # Add players with agents
    for ps in config.players:
        agent = create_agent_from_db(ps.agent_id)
        game.add_player(ps.agent_id, name_map[ps.agent_id], agent, buy_in=ps.chips)

    session = GameSession(
        session_id=session_id,
        game=game,
        status="pending_start",
        _num_hands=count,
        lab_config=config,
    )
    _active_games[session_id] = session
    return session


async def run_game(session_id: str, num_hands: int = 10) -> dict:
    """Run a game session asynchronously."""
    session = _active_games.get(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    session.status = "running"
    db = get_db()
    db.execute(
        "UPDATE game_sessions SET status='running', started_at=? WHERE session_id=?",
        (now_iso(), session_id),
    )
    db.commit()
    db.close()

    hand_num = 0

    # Set up human agent callback if there's a human player
    if session.human_player_id:
        human_agent = HumanAgent.get_agent(session.human_player_id)
        if human_agent and session.on_event:
            human_agent._on_human_turn_callback = session.on_event

    async def on_hand_complete(result: HandResult) -> None:
        nonlocal hand_num
        hand_num += 1
        hand_data = _serialize_hand(result, session_id, hand_num)
        session.hand_results.append(hand_data)
        _save_hand_to_db(hand_data)
        if session.on_event:
            await session.on_event({"type": "hand_complete", "data": hand_data})

    async def on_action(event: dict) -> None:
        if session.on_event:
            await session.on_event(event)

    result = await session.game.run(
        num_hands,
        on_hand_complete=on_hand_complete,
        on_action=on_action,
        stop_event=session.stop_event,
    )
    session.status = "finished"

    # Notify frontend that game is done
    if session.on_event:
        await session.on_event({
            "type": "game_finished",
            "data": {
                "session_id": session_id,
                "total_hands": result.total_hands,
                "final_chips": result.final_chips,
            },
        })

    db = get_db()
    db.execute(
        "UPDATE game_sessions SET status='finished', finished_at=? WHERE session_id=?",
        (now_iso(), session_id),
    )
    db.commit()
    db.close()

    return {
        "session_id": session_id,
        "total_hands": result.total_hands,
        "final_chips": result.final_chips,
    }


async def run_lab_game(session_id: str) -> dict:
    """Run a Hand Lab session: execute hands with preset cards, streaming events via WebSocket."""
    from backend.services.hand_lab import compute_equity, _build_summary
    from backend.engine.card import Card
    from backend.engine.game_runner import GameRunner
    from backend.engine.game_state import PlayerState

    session = _active_games.get(session_id)
    if not session or not session.lab_config:
        raise ValueError(f"Lab session {session_id} not found")

    config = session.lab_config
    num_hands = session._num_hands
    session.status = "running"

    # Parse preset cards once
    preset_hole: dict[str, list[Card]] = {}
    all_preset_cards: list[Card] = []
    for p in config.players:
        if p.hole_cards:
            cards = [Card.from_string(c) for c in p.hole_cards]
            preset_hole[p.agent_id] = cards
            all_preset_cards.extend(cards)

    preset_community = [Card.from_string(c) for c in config.community_cards]
    all_preset_cards.extend(preset_community)

    name_map: dict[str, str] = {
        ps.agent_id: _get_agent_name(ps.agent_id) for ps in config.players
    }

    hand_num = 0
    all_hand_results: list[dict] = []

    for _ in range(num_hands):
        if session.stop_event.is_set():
            break

        hand_num += 1
        # Capture starting chips
        starting_chips = {p.player_id: p.chips for p in session.game.players}

        # Prepare players for this hand
        hand_players = []
        for p in session.game.players:
            if p.chips <= 0:
                continue
            ps = PlayerState(
                player_id=p.player_id,
                display_name=p.display_name,
                chips=p.chips,
                seat_index=p.seat_index,
                hole_cards=list(preset_hole.get(p.player_id, [])),
            )
            hand_players.append(ps)

        if len(hand_players) < 2:
            break

        active_agents = {p.player_id: session.game.agents[p.player_id] for p in hand_players}
        runner = GameRunner(
            players=hand_players,
            agents=active_agents,
            small_blind=config.small_blind,
            big_blind=config.big_blind,
            dealer_index=session.game.dealer_index % len(hand_players),
            street_delay_ms=session.game.config.street_delay_ms,
        )

        # Remove preset cards from deck
        if all_preset_cards:
            runner.deck.remove_cards(all_preset_cards)
        # Preset community cards
        if preset_community:
            runner.state.community_cards = list(preset_community)

        # Track equity state for this hand
        folded: set[str] = set()
        live_player_cards: dict[str, list[Card]] = {}

        async def on_action(event: dict, _folded=folded, _live_cards=live_player_cards, _runner=runner) -> None:
            etype = event.get("type")
            data = event.get("data", {})

            if etype == "hand_start":
                # Collect hole cards for equity
                for pid, info in data.get("players", {}).items():
                    for ps in config.players:
                        if name_map[ps.agent_id] == pid:
                            hole = info.get("hole_cards", [])
                            if hole:
                                _live_cards[ps.agent_id] = [Card.from_string(c) for c in hole]
                            break
                # Augment with equity
                equity = compute_equity(
                    _live_cards, list(_runner.state.community_cards), _folded, name_map,
                )
                event["data"]["equity"] = equity

            elif etype == "street_start":
                equity = compute_equity(
                    _live_cards, list(_runner.state.community_cards), _folded, name_map,
                )
                event["data"]["equity"] = equity

            elif etype == "player_action":
                display_pid = data.get("player_id", "")
                if data.get("action") == "fold":
                    for ps in config.players:
                        if name_map[ps.agent_id] == display_pid:
                            _folded.add(ps.agent_id)
                            break

            # Broadcast via WebSocket
            if session.on_event:
                await session.on_event(event)

        runner.on_action = on_action
        result = await runner.run_hand()

        # Sync chips back
        for p in session.game.players:
            if p.player_id in result.final_chips:
                p.chips = result.final_chips[p.player_id]

        # Compute chip changes
        chip_changes = {}
        for p in session.game.players:
            start = starting_chips.get(p.player_id, 0)
            chip_changes[p.player_id] = p.chips - start
        result.starting_chips = starting_chips
        result.chip_changes = chip_changes

        session.game.dealer_index = (session.game.dealer_index + 1) % len(session.game.players)

        # Build hand_complete data
        hand_data = _serialize_hand(result, session_id, hand_num)

        # Add equity to hand_complete
        final_equity = compute_equity(
            live_player_cards, list(result.community_cards), folded, name_map,
        )
        hand_data["equity"] = final_equity

        session.hand_results.append(hand_data)
        all_hand_results.append(hand_data)

        if session.on_event:
            await session.on_event({"type": "hand_complete", "data": hand_data})

        # Reset per-hand tracking for next hand
        folded.clear()
        live_player_cards.clear()

        # Pause between hands
        if session.game.config.hand_delay_ms > 0 and hand_num < num_hands:
            await asyncio.sleep(session.game.config.hand_delay_ms / 1000)

    # Build summary for multi-run
    session.status = "finished"
    player_names = [name_map[ps.agent_id] for ps in config.players]
    summary = None
    if num_hands > 1:
        summary = _build_summary(all_hand_results, player_names)

    if session.on_event:
        await session.on_event({
            "type": "lab_finished",
            "data": {
                "session_id": session_id,
                "total_hands": hand_num,
                "final_chips": {name_map.get(p.player_id, p.player_id): p.chips for p in session.game.players},
                "summary": summary,
            },
        })

    return {"session_id": session_id, "total_hands": hand_num}


def get_session(session_id: str) -> GameSession | None:
    return _active_games.get(session_id)


def stop_game(session_id: str) -> bool:
    """Signal a running game to stop after the current hand."""
    session = _active_games.get(session_id)
    if not session:
        return False
    if session.status not in ("running", "pending_start"):
        return False
    session.stop_event.set()
    return True


def trigger_game_start(session_id: str) -> bool:
    """Called by WebSocket handler to start the game after on_event is registered.
    Returns True if game was started, False if already running/finished."""
    session = _active_games.get(session_id)
    if not session or session.status != "pending_start":
        return False
    if not session.on_event:
        return False
    # Launch game as background task — lab or regular
    if session.lab_config:
        asyncio.create_task(run_lab_game(session_id))
    else:
        asyncio.create_task(run_game(session_id, session._num_hands))
    return True


def list_sessions() -> list[dict]:
    db = get_db()
    rows = db.execute(
        "SELECT session_id, status, small_blind, big_blind, created_at FROM game_sessions ORDER BY created_at DESC"
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def _get_agent_name(agent_id: str) -> str:
    """Get display_name for an agent from DB."""
    db = get_db()
    row = db.execute("SELECT display_name FROM agents WHERE agent_id=?", (agent_id,)).fetchone()
    db.close()
    return row["display_name"] if row else agent_id


def _serialize_hand(result: HandResult, session_id: str, hand_num: int) -> dict:
    # Map agent IDs to display names for frontend readability
    name_map = {}
    for pid in result.final_chips.keys():
        name_map[pid] = _get_agent_name(pid)

    return {
        "hand_id": result.hand_id,
        "session_id": session_id,
        "hand_number": hand_num,
        "community_cards": [str(c) for c in result.community_cards],
        "pot_total": sum(result.winners.values()),
        "winners": {name_map.get(k, k): v for k, v in result.winners.items()},
        "final_chips": {name_map.get(k, k): v for k, v in result.final_chips.items()},
        "actions": [
            {
                "player_id": a.player_id,  # Already display_name from game_runner
                "street": a.street,
                "action": a.action,
                "amount": a.amount,
                "round_bet": a.round_bet,
                "pot_after": a.pot_after,
                "thinking": a.thinking,
                "is_timeout": a.is_timeout,
                "is_fallback": a.is_fallback,
                "input_tokens": a.input_tokens,
                "output_tokens": a.output_tokens,
                "llm_latency_ms": a.llm_latency_ms,
                "decision_ms": a.decision_ms,
            }
            for a in result.action_history
        ],
        "player_hands": {
            name_map.get(pid, pid): str(score) for pid, score in result.player_hands.items()
        },
        "player_cards": {
            name_map.get(pid, pid): [str(c) for c in cards] for pid, cards in result.player_cards.items()
        },
        "starting_chips": {name_map.get(k, k): v for k, v in result.starting_chips.items()},
        "chip_changes": {name_map.get(k, k): v for k, v in result.chip_changes.items()},
    }


def _save_hand_to_db(hand: dict) -> None:
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO hand_records (hand_id, session_id, hand_number, community_cards, pot_total, winners_json, actions_json, player_cards_json, chip_changes_json, started_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            hand["hand_id"], hand["session_id"], hand["hand_number"],
            json.dumps(hand["community_cards"]),
            hand["pot_total"],
            json.dumps(hand["winners"]),
            json.dumps(hand["actions"]),
            json.dumps(hand.get("player_cards", {})),
            json.dumps(hand.get("chip_changes", {})),
            now_iso(),
        ),
    )
    db.commit()
    db.close()
