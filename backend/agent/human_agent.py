"""Human agent that awaits decisions via WebSocket."""
from __future__ import annotations

import asyncio
from typing import Any

from backend.agent.base_agent import BaseAgent
from backend.engine.betting_round import BettingAction, PlayerAction


class HumanAgent(BaseAgent):
    """Agent that pauses game loop and waits for human decision via WebSocket."""

    # Class-level registry to map player_id to HumanAgent instance
    _registry: dict[str, "HumanAgent"] = {}

    def __init__(self, agent_id: str, display_name: str, timeout_seconds: float = 60.0) -> None:
        super().__init__(agent_id, display_name)
        self.timeout_seconds = timeout_seconds
        self._pending_future: asyncio.Future[PlayerAction] | None = None
        self._valid_actions: list[BettingAction] = []
        self._game_view: dict[str, Any] = {}
        # Register this instance
        HumanAgent._registry[agent_id] = self

    async def decide(
        self,
        game_view: dict[str, Any],
        valid_actions: list[BettingAction],
    ) -> tuple[PlayerAction, dict[str, Any]]:
        """Wait for human decision via WebSocket.

        Creates a Future that will be resolved when submit_decision() is called
        by the WebSocket handler, or timeout occurs.
        """
        self._valid_actions = valid_actions
        self._game_view = game_view
        self._pending_future = asyncio.get_event_loop().create_future()

        # Store the callback to broadcast the human_turn event
        # This will be set by game_service when creating the game
        on_human_turn = getattr(self, "_on_human_turn_callback", None)

        if on_human_turn:
            # Build valid action names for frontend
            action_names = [a.value for a in valid_actions]

            # Calculate call amount and raise limits from game_view
            # Find my player info from the players list
            my_player_info = None
            for p in game_view.get("players", []):
                if p.get("player_id") == self.agent_id:
                    my_player_info = p
                    break

            my_chips = my_player_info.get("chips", 0) if my_player_info else 0
            my_current_bet = my_player_info.get("current_bet", 0) if my_player_info else 0

            # Calculate call amount: max current bet - my current bet
            max_current_bet = 0
            for p in game_view.get("players", []):
                max_current_bet = max(max_current_bet, p.get("current_bet", 0))
            call_amount = max(0, max_current_bet - my_current_bet)

            # Min raise is typically current bet + big blind (simplified)
            # Get big blind from game config if available, default to 100
            big_blind = game_view.get("big_blind", 100)
            min_raise = max_current_bet + big_blind if max_current_bet > 0 else big_blind

            await on_human_turn({
                "type": "human_turn",
                "data": {
                    "player_id": self.agent_id,  # Use agent_id, not display_name
                    "valid_actions": action_names,
                    "call_amount": call_amount,
                    "min_raise": min_raise,
                    "max_raise": my_chips,
                    "current_bet": my_current_bet,
                    "game_view": game_view,
                    "timeout_seconds": self.timeout_seconds,
                },
            })

        try:
            # Wait for human decision with timeout
            action = await asyncio.wait_for(
                self._pending_future,
                timeout=self.timeout_seconds
            )
            metadata = {
                "thinking": "",
                "is_timeout": False,
                "is_fallback": False,
                "input_tokens": 0,
                "output_tokens": 0,
                "llm_latency_ms": 0.0,
                "decision_ms": 0.0,
            }
        except asyncio.TimeoutError:
            # Timeout: default to FOLD
            action = PlayerAction(self.agent_id, BettingAction.FOLD)
            metadata = {
                "thinking": "Timeout - auto fold",
                "is_timeout": True,
                "is_fallback": True,
                "input_tokens": 0,
                "output_tokens": 0,
                "llm_latency_ms": 0.0,
                "decision_ms": 0.0,
            }
        finally:
            self._pending_future = None

        return action, metadata

    def submit_decision(self, action: PlayerAction) -> bool:
        """Submit a decision from the WebSocket handler.

        Returns True if the decision was accepted, False if no pending decision.
        """
        if self._pending_future and not self._pending_future.done():
            # Validate the action is in valid_actions
            if action.action in self._valid_actions:
                self._pending_future.set_result(action)
                return True
        return False

    def cancel_pending(self) -> None:
        """Cancel any pending decision (e.g., when game ends)."""
        if self._pending_future and not self._pending_future.done():
            self._pending_future.cancel()
            self._pending_future = None

    @classmethod
    def get_agent(cls, agent_id: str) -> "HumanAgent | None":
        """Get a HumanAgent instance by agent_id."""
        return cls._registry.get(agent_id)

    @classmethod
    def remove_agent(cls, agent_id: str) -> None:
        """Remove a HumanAgent from registry (cleanup)."""
        if agent_id in cls._registry:
            agent = cls._registry[agent_id]
            agent.cancel_pending()
            del cls._registry[agent_id]
