"""Hand Lab service: run preset poker scenarios for testing agent decisions."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from backend.engine.card import Card
from backend.engine.equity import EquityCalculator
from backend.engine.game_runner import GameRunner, HandResult
from backend.engine.game_state import PlayerState
from backend.services.game_service import create_agent_from_db, _get_agent_name


@dataclass
class PlayerSetup:
    agent_id: str
    chips: int = 5000
    hole_cards: list[str] = field(default_factory=list)  # e.g. ["Ah", "Kd"] or [] for random
    seat_index: int = 0


@dataclass
class ScenarioConfig:
    players: list[PlayerSetup]
    community_cards: list[str] = field(default_factory=list)  # up to 5
    small_blind: int = 50
    big_blind: int = 100
    dealer_index: int = 0


class HandLab:
    """Execute preset poker scenarios."""

    def __init__(self, config: ScenarioConfig) -> None:
        self.config = config
        self._validate()

    def _validate(self) -> None:
        """Validate scenario configuration."""
        if len(self.config.players) < 2:
            raise ValueError("Need at least 2 players")
        if len(self.config.community_cards) > 5:
            raise ValueError("Community cards cannot exceed 5")

        # Validate all preset cards are parseable and unique
        all_cards: list[Card] = []
        for p in self.config.players:
            if p.hole_cards:
                if len(p.hole_cards) != 2:
                    raise ValueError(f"Player {p.agent_id} must have 0 or 2 hole cards")
                for c in p.hole_cards:
                    all_cards.append(Card.from_string(c))
        for c in self.config.community_cards:
            all_cards.append(Card.from_string(c))
        if len(all_cards) != len(set(all_cards)):
            raise ValueError("Duplicate cards in scenario")

    def _compute_equity(
        self,
        player_cards: dict[str, list[Card]],
        community: list[Card],
        folded: set[str],
        name_map: dict[str, str],
    ) -> list[dict]:
        """Compute equity for active (non-folded) players with known cards."""
        active_ids = [pid for pid in player_cards if pid not in folded and player_cards[pid]]
        if len(active_ids) < 2:
            # Can't compute meaningful equity with < 2 active players
            return [
                {
                    "player_id": name_map.get(pid, pid),
                    "win_pct": 100.0 if pid in active_ids else 0.0,
                    "tie_pct": 0.0,
                }
                for pid in player_cards
            ]

        active_cards = [player_cards[pid] for pid in active_ids]
        try:
            results = EquityCalculator.calculate(active_cards, community, num_simulations=2000)
        except (ValueError, Exception):
            return []

        # Build full equity list including folded players at 0%
        equity = []
        active_idx = 0
        for pid in player_cards:
            if pid in folded or not player_cards[pid]:
                equity.append({"player_id": name_map.get(pid, pid), "win_pct": 0.0, "tie_pct": 0.0})
            else:
                r = results[active_idx]
                equity.append({
                    "player_id": name_map.get(pid, pid),
                    "win_pct": round(r.win_pct * 100, 1),
                    "tie_pct": round(r.tie_pct * 100, 1),
                })
                active_idx += 1
        return equity

    async def run_once(self) -> dict:
        """Execute the scenario once and return serialized result with step-by-step data."""
        # Parse preset cards
        preset_hole: dict[str, list[Card]] = {}
        all_preset_cards: list[Card] = []
        for p in self.config.players:
            if p.hole_cards:
                cards = [Card.from_string(c) for c in p.hole_cards]
                preset_hole[p.agent_id] = cards
                all_preset_cards.extend(cards)

        preset_community = [Card.from_string(c) for c in self.config.community_cards]
        all_preset_cards.extend(preset_community)

        # Build name map
        name_map: dict[str, str] = {}
        for ps in self.config.players:
            name_map[ps.agent_id] = _get_agent_name(ps.agent_id)

        # Build PlayerState list
        players = [
            PlayerState(
                player_id=ps.agent_id,
                display_name=name_map[ps.agent_id],
                chips=ps.chips,
                seat_index=ps.seat_index,
                hole_cards=preset_hole.get(ps.agent_id, []),
            )
            for ps in self.config.players
        ]

        # Load agents
        agents = {}
        for ps in self.config.players:
            agent = create_agent_from_db(ps.agent_id)
            agents[ps.agent_id] = agent

        # Create GameRunner
        runner = GameRunner(
            players=players,
            agents=agents,
            small_blind=self.config.small_blind,
            big_blind=self.config.big_blind,
            dealer_index=self.config.dealer_index,
        )

        # Remove preset cards from deck
        if all_preset_cards:
            runner.deck.remove_cards(all_preset_cards)

        # Preset community cards
        if preset_community:
            runner.state.community_cards = list(preset_community)

        # Collect steps via on_action callback
        steps: list[dict] = []
        folded: set[str] = set()
        # Track player cards (will be filled after hand_start)
        live_player_cards: dict[str, list[Card]] = {}

        async def collect_step(event: dict) -> None:
            etype = event.get("type")
            data = event.get("data", {})

            if etype == "hand_start":
                # Collect player hole cards for equity
                for pid, info in data.get("players", {}).items():
                    # pid here is display_name, we need agent_id for equity
                    for ps in self.config.players:
                        if name_map[ps.agent_id] == pid:
                            hole = info.get("hole_cards", [])
                            if hole:
                                live_player_cards[ps.agent_id] = [Card.from_string(c) for c in hole]
                            break

                # Compute preflop equity
                equity = self._compute_equity(
                    live_player_cards,
                    list(runner.state.community_cards),
                    folded,
                    name_map,
                )
                steps.append({
                    "type": "hand_start",
                    "community_cards": [str(c) for c in runner.state.community_cards],
                    "pot": data.get("pot", 0),
                    "equity": equity,
                    "players": data.get("players", {}),
                })

            elif etype == "street_start":
                community = [str(c) for c in runner.state.community_cards]
                equity = self._compute_equity(
                    live_player_cards,
                    list(runner.state.community_cards),
                    folded,
                    name_map,
                )
                steps.append({
                    "type": "street",
                    "street": data.get("street", ""),
                    "community_cards": community,
                    "pot": data.get("pot", 0),
                    "equity": equity,
                })

            elif etype == "player_action":
                display_pid = data.get("player_id", "")
                if data.get("action") == "fold":
                    # Find agent_id from display name
                    for ps in self.config.players:
                        if name_map[ps.agent_id] == display_pid:
                            folded.add(ps.agent_id)
                            break

                steps.append({
                    "type": "action",
                    "player_id": display_pid,
                    "street": data.get("street", ""),
                    "action": data.get("action", ""),
                    "amount": data.get("amount", 0),
                    "round_bet": data.get("round_bet", 0),
                    "pot_after": data.get("pot_after", 0),
                    "thinking": data.get("thinking", ""),
                })

            elif etype == "player_thinking":
                steps.append({
                    "type": "thinking",
                    "player_id": data.get("player_id", ""),
                    "street": data.get("street", ""),
                })

        runner.on_action = collect_step

        # Run the hand
        result = await runner.run_hand()

        # Final result step with deterministic equity
        final_equity = self._compute_equity(
            live_player_cards,
            list(result.community_cards),
            folded,
            name_map,
        )
        steps.append({
            "type": "result",
            "community_cards": [str(c) for c in result.community_cards],
            "pot": sum(result.winners.values()),
            "equity": final_equity,
            "winners": {name_map.get(k, k): v for k, v in result.winners.items()},
            "chip_changes": {
                name_map.get(pid, pid): result.final_chips.get(pid, 0) - ps.chips
                for ps, pid in zip(self.config.players, [p.agent_id for p in self.config.players])
            },
        })

        serialized = _serialize_lab_result(result, self.config, steps[0].get("equity") if steps else None)
        serialized["steps"] = steps
        return serialized

    async def run_multiple(self, count: int) -> dict:
        """Run scenario N times and return summary statistics."""
        results = []
        for _ in range(count):
            results.append(await self.run_once())

        player_names = [
            _get_agent_name(p.agent_id) for p in self.config.players
        ]
        summary = _build_summary(results, player_names)

        return {
            "count": len(results),
            "results": results,
            "summary": summary,
        }


def _serialize_lab_result(
    result: HandResult,
    config: ScenarioConfig,
    equity: list[dict] | None,
) -> dict:
    """Serialize a HandResult for the Hand Lab API."""
    name_map = {}
    for pid in result.final_chips.keys():
        name_map[pid] = _get_agent_name(pid)

    starting = {ps.agent_id: ps.chips for ps in config.players}
    chip_changes = {
        name_map.get(pid, pid): result.final_chips.get(pid, 0) - starting.get(pid, 0)
        for pid in result.final_chips
    }

    return {
        "hand_id": result.hand_id,
        "community_cards": [str(c) for c in result.community_cards],
        "pot_total": sum(result.winners.values()),
        "winners": {name_map.get(k, k): v for k, v in result.winners.items()},
        "final_chips": {name_map.get(k, k): v for k, v in result.final_chips.items()},
        "chip_changes": chip_changes,
        "actions": [
            {
                "player_id": a.player_id,
                "street": a.street,
                "action": a.action,
                "amount": a.amount,
                "round_bet": a.round_bet,
                "pot_after": a.pot_after,
                "thinking": a.thinking,
            }
            for a in result.action_history
        ],
        "player_cards": {
            name_map.get(pid, pid): [str(c) for c in cards]
            for pid, cards in result.player_cards.items()
        },
        "player_hands": {
            name_map.get(pid, pid): str(score)
            for pid, score in result.player_hands.items()
        },
        "equity": equity,
    }


def _build_summary(results: list[dict], player_names: list[str]) -> dict:
    """Build summary statistics from multiple runs."""
    n = len(results)
    wins: dict[str, int] = {name: 0 for name in player_names}
    total_profit: dict[str, int] = {name: 0 for name in player_names}
    total_pot = 0

    for r in results:
        total_pot += r.get("pot_total", 0)
        for name in player_names:
            change = r.get("chip_changes", {}).get(name, 0)
            total_profit[name] += change
            if name in r.get("winners", {}):
                wins[name] += 1

    return {
        "win_rate": {name: round(wins[name] / n * 100, 1) for name in player_names},
        "avg_profit": {name: round(total_profit[name] / n) for name in player_names},
        "avg_pot": round(total_pot / n) if n > 0 else 0,
        "total_runs": n,
    }
