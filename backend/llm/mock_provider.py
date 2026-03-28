"""Mock LLM provider for testing without real API calls."""
from __future__ import annotations

import random
import time

from backend.llm.base_provider import BaseLLMProvider, LLMCallResult


class MockLLMProvider(BaseLLMProvider):
    """Returns configurable fixed responses. For tests and CLI demos."""

    def __init__(
        self,
        style: str = "random",
        delay_ms: float = 50.0,
        fail_rate: float = 0.0,
    ) -> None:
        self.style = style  # "random", "aggressive", "passive", "fixed"
        self.delay_ms = delay_ms
        self.fail_rate = fail_rate
        self.call_count = 0
        self._fixed_response: str = "ACTION: call"

    def set_fixed_response(self, response: str) -> None:
        self._fixed_response = response
        self.style = "fixed"

    async def chat(self, messages: list[dict]) -> LLMCallResult:
        self.call_count += 1
        start = time.monotonic()

        # Simulate failure
        if random.random() < self.fail_rate:
            return LLMCallResult(
                text="", input_tokens=0, output_tokens=0, total_tokens=0,
                latency_ms=self.delay_ms, status="error",
                error_message="Simulated error",
                provider_name="mock", model_name="mock-v1",
            )

        # Simulate latency
        if self.delay_ms > 0:
            import asyncio
            await asyncio.sleep(self.delay_ms / 1000)

        text = self._generate_response(messages)
        latency = (time.monotonic() - start) * 1000
        input_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
        output_tokens = len(text) // 4

        return LLMCallResult(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            latency_ms=latency,
            status="success",
            provider_name="mock",
            model_name="mock-v1",
        )

    def _generate_response(self, messages: list[dict]) -> str:
        if self.style == "fixed":
            return f"THINKING: 按照固定策略行动\n{self._fixed_response}"

        # Extract context to make somewhat realistic decisions
        user_msg = ""
        for m in messages:
            if m.get("role") == "user":
                user_msg = m.get("content", "")

        if self.style == "aggressive":
            return self._aggressive_response(user_msg)
        elif self.style == "passive":
            return self._passive_response(user_msg)
        else:
            return self._random_response(user_msg)

    def _random_response(self, context: str) -> str:
        actions = ["fold", "check", "call", "raise"]
        if "check" not in context.lower():
            actions = [a for a in actions if a != "check"]
        action = random.choice(actions)
        amount = random.randint(50, 500) if action == "raise" else 0
        thinking = "让我随机决定一下..."
        return (
            f"THINKING: {thinking}\n"
            f"ACTION: {action}\n"
            f"AMOUNT: {amount}"
        )

    def _aggressive_response(self, context: str) -> str:
        import random
        # 50% chance to call/check to let game proceed to flop
        if random.random() < 0.5:
            if "check" in context.lower():
                return "THINKING: 看看公共牌\nACTION: check"
            return "THINKING: 跟注看翻牌\nACTION: call"
        if "raise" in context.lower() or "call" in context.lower():
            return "THINKING: 我要施压！\nACTION: raise\nAMOUNT: 300"
        return "THINKING: 先加注看看\nACTION: raise\nAMOUNT: 200"

    def _passive_response(self, context: str) -> str:
        if "check" in context.lower():
            return "THINKING: 看看再说\nACTION: check"
        return "THINKING: 跟注看看\nACTION: call"

    def get_provider_name(self) -> str:
        return "mock"
