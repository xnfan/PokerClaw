"""Base agent interface for all player types."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.engine.betting_round import BettingAction, PlayerAction


class BaseAgent(ABC):
    """Abstract base class for all agents (LLM, human, rule-based)."""

    def __init__(self, agent_id: str, display_name: str) -> None:
        self.agent_id = agent_id
        self.display_name = display_name

    @abstractmethod
    async def decide(
        self,
        game_view: dict[str, Any],
        valid_actions: list[BettingAction],
    ) -> tuple[PlayerAction, dict[str, Any]]:
        """Make a decision given the current game state.

        Returns:
            tuple of (PlayerAction, metadata_dict)
            metadata_dict contains: thinking, is_timeout, is_fallback,
            input_tokens, output_tokens, llm_latency_ms, decision_ms
        """
        ...

    async def notify_hand_result(self, result: Any) -> None:
        """Called after a hand completes. Override for learning agents."""
        pass
