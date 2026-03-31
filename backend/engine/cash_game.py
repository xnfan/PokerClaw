"""Cash game session manager - runs multiple hands continuously."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from backend.engine.game_runner import GameRunner, HandResult
from backend.engine.game_state import PlayerState

if TYPE_CHECKING:
    from backend.agent.base_agent import BaseAgent


@dataclass
class CashGameConfig:
    small_blind: int = 50
    big_blind: int = 100
    min_buy_in: int = 2000
    max_buy_in: int = 20000
    max_players: int = 9


@dataclass
class SessionResult:
    session_id: str
    hand_results: list[HandResult]
    final_chips: dict[str, int]
    total_hands: int


class CashGame:
    """Manages a cash game session with multiple hands."""

    def __init__(self, config: CashGameConfig | None = None) -> None:
        self.session_id = str(uuid.uuid4())[:8]
        self.config = config or CashGameConfig()
        self.players: list[PlayerState] = []
        self.agents: dict[str, "BaseAgent"] = {}
        self.hand_results: list[HandResult] = []
        self.dealer_index = 0
        self._hand_count = 0

    def add_player(
        self,
        player_id: str,
        display_name: str,
        agent: "BaseAgent",
        buy_in: int | None = None,
    ) -> None:
        """Add a player to the table."""
        if len(self.players) >= self.config.max_players:
            raise ValueError("Table is full")
        buy_in = buy_in or self.config.min_buy_in
        seat_index = len(self.players)
        player = PlayerState(
            player_id=player_id,
            display_name=display_name,
            chips=buy_in,
            seat_index=seat_index,
        )
        self.players.append(player)
        self.agents[player_id] = agent

    def remove_player(self, player_id: str) -> None:
        """Remove a player from the table (stub for future use)."""
        self.players = [p for p in self.players if p.player_id != player_id]
        self.agents.pop(player_id, None)

    def rebuy(self, player_id: str, amount: int) -> None:
        """Allow a player to rebuy (stub for future use)."""
        for p in self.players:
            if p.player_id == player_id:
                p.chips += amount
                return
        raise ValueError(f"Player {player_id} not found")

    async def run(
        self,
        num_hands: int,
        on_hand_complete: Any = None,
        on_action: Any = None,
        stop_event: Any = None,
    ) -> SessionResult:
        """Run a session of num_hands hands."""
        if len(self.players) < 2:
            raise ValueError("Need at least 2 players")

        for _ in range(num_hands):
            # Check for stop signal
            if stop_event and stop_event.is_set():
                break
            # Capture starting chips before the hand
            starting_chips = {p.player_id: p.chips for p in self.players}
            # Reset per-hand state for each player
            hand_players = self._prepare_hand_players()
            if len(hand_players) < 2:
                break  # Not enough players to continue
            active_agents = {
                p.player_id: self.agents[p.player_id] for p in hand_players
            }
            runner = GameRunner(
                players=hand_players,
                agents=active_agents,
                small_blind=self.config.small_blind,
                big_blind=self.config.big_blind,
                dealer_index=self.dealer_index % len(hand_players),
            )
            # Pass action callback to runner
            if on_action:
                runner.on_action = on_action
            result = await runner.run_hand()
            self.hand_results.append(result)
            # Sync chips back to session players
            for p in self.players:
                if p.player_id in result.final_chips:
                    p.chips = result.final_chips[p.player_id]
            # Compute chip changes
            chip_changes = {}
            for p in self.players:
                start = starting_chips.get(p.player_id, 0)
                chip_changes[p.player_id] = p.chips - start
            result.starting_chips = starting_chips
            result.chip_changes = chip_changes
            self.dealer_index = (self.dealer_index + 1) % len(self.players)
            self._hand_count += 1
            if on_hand_complete:
                await on_hand_complete(result)

        return SessionResult(
            session_id=self.session_id,
            hand_results=self.hand_results,
            final_chips={p.player_id: p.chips for p in self.players},
            total_hands=self._hand_count,
        )

    def _prepare_hand_players(self) -> list[PlayerState]:
        """Create fresh PlayerState copies for a new hand (only players with chips)."""
        return [
            PlayerState(
                player_id=p.player_id,
                display_name=p.display_name,
                chips=p.chips,
                seat_index=p.seat_index,
            )
            for p in self.players
            if p.chips > 0
        ]
