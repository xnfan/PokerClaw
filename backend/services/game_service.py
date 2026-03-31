"""Game service: orchestrates creating/running games, bridges API and engine."""
from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from backend.agent.llm_agent import LLMAgent
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
    status: str = "waiting"  # waiting / running / finished
    hand_results: list[dict] = field(default_factory=list)
    on_event: Callable | None = None  # WebSocket broadcast callback
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)


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
            style=mock_map.get(row["play_style"], "random"), delay_ms=800
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
) -> GameSession:
    """Create a new game session with the given agents."""
    config = CashGameConfig(small_blind=small_blind, big_blind=big_blind)
    game = CashGame(config)
    session_id = game.session_id

    for aid in agent_ids:
        agent = create_agent_from_db(aid)
        game.add_player(aid, agent.display_name, agent, buy_in=buy_in)

    session = GameSession(session_id=session_id, game=game)
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


def get_session(session_id: str) -> GameSession | None:
    return _active_games.get(session_id)


def stop_game(session_id: str) -> bool:
    """Signal a running game to stop after the current hand."""
    session = _active_games.get(session_id)
    if not session:
        return False
    session.stop_event.set()
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
