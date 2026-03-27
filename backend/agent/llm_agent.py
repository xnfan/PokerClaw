"""LLM-powered poker agent with timeout, retry, and monitoring."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from backend.agent.action_parser import ActionParser
from backend.agent.base_agent import BaseAgent
from backend.agent.decision_context import DecisionContextBuilder
from backend.agent.personality import PersonalityProfile
from backend.engine.betting_round import BettingAction, PlayerAction
from backend.llm.base_provider import BaseLLMProvider
from backend.monitoring.agent_monitor import AgentMonitor


# Default 30-second timeout for agent decisions
DEFAULT_DECISION_TIMEOUT = 30.0


class LLMAgent(BaseAgent):
    """Agent that uses an LLM to make poker decisions."""

    def __init__(
        self,
        agent_id: str,
        display_name: str,
        personality: PersonalityProfile,
        llm_provider: BaseLLMProvider,
        monitor: AgentMonitor | None = None,
        decision_timeout: float = DEFAULT_DECISION_TIMEOUT,
        max_retries: int = 1,
    ) -> None:
        super().__init__(agent_id, display_name)
        self.personality = personality
        self.llm_provider = llm_provider
        self.monitor = monitor or AgentMonitor()
        self.decision_timeout = decision_timeout
        self.max_retries = max_retries
        self.last_thinking: str = ""
        self.last_metrics: dict[str, Any] = {}

    async def decide(
        self,
        game_view: dict[str, Any],
        valid_actions: list[BettingAction],
    ) -> tuple[PlayerAction, dict[str, Any]]:
        """Make a decision with timeout, retry, and monitoring."""
        start_time = time.monotonic()
        metadata: dict[str, Any] = {
            "thinking": "",
            "is_timeout": False,
            "is_fallback": False,
            "input_tokens": 0,
            "output_tokens": 0,
            "llm_latency_ms": 0.0,
            "decision_ms": 0.0,
        }

        try:
            action = await asyncio.wait_for(
                self._decide_inner(game_view, valid_actions, metadata),
                timeout=self.decision_timeout,
            )
            metadata["decision_ms"] = (time.monotonic() - start_time) * 1000
            self.monitor.record_decision(
                self.agent_id, "success", start_time
            )
            return action, metadata

        except asyncio.TimeoutError:
            metadata["is_timeout"] = True
            metadata["is_fallback"] = True
            metadata["decision_ms"] = (time.monotonic() - start_time) * 1000
            self.monitor.record_decision(
                self.agent_id, "timeout", start_time
            )
            return self._fallback(valid_actions), metadata

        except Exception as e:
            metadata["is_fallback"] = True
            metadata["decision_ms"] = (time.monotonic() - start_time) * 1000
            self.monitor.record_decision(
                self.agent_id, "exception", start_time, error=str(e)
            )
            return self._fallback(valid_actions), metadata

    async def _decide_inner(
        self,
        game_view: dict[str, Any],
        valid_actions: list[BettingAction],
        metadata: dict[str, Any],
    ) -> PlayerAction:
        """Core decision logic: build context → call LLM → parse action."""
        # Build context text
        context_text = DecisionContextBuilder.build(game_view, valid_actions)
        messages = self.personality.build_messages(context_text)

        # Call LLM (with retry on error)
        llm_result = await self.llm_provider.chat(messages)
        self.monitor.record_llm_call(self.agent_id, llm_result)
        metadata["input_tokens"] = llm_result.input_tokens
        metadata["output_tokens"] = llm_result.output_tokens
        metadata["llm_latency_ms"] = llm_result.latency_ms

        # Retry once on error
        if llm_result.status == "error" and self.max_retries > 0:
            llm_result = await self.llm_provider.chat(messages)
            self.monitor.record_llm_call(
                self.agent_id, llm_result, is_retry=True
            )
            metadata["input_tokens"] += llm_result.input_tokens
            metadata["output_tokens"] += llm_result.output_tokens
            metadata["llm_latency_ms"] += llm_result.latency_ms

        # If still failed after retry, fallback
        if llm_result.status != "success":
            metadata["is_fallback"] = True
            return self._fallback(valid_actions)

        # Parse action from LLM output
        self.last_thinking = ActionParser.extract_thinking(llm_result.text)
        metadata["thinking"] = self.last_thinking
        action = ActionParser.parse(
            llm_result.text, valid_actions, self.agent_id
        )
        return action

    def _fallback(self, valid_actions: list[BettingAction]) -> PlayerAction:
        """Fallback: check if possible, otherwise fold."""
        if BettingAction.CHECK in valid_actions:
            return PlayerAction(self.agent_id, BettingAction.CHECK)
        return PlayerAction(self.agent_id, BettingAction.FOLD)
