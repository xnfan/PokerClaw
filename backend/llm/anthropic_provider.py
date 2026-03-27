"""Anthropic Claude LLM provider implementation."""
from __future__ import annotations

import time
from typing import Any

from backend.llm.base_provider import BaseLLMProvider, LLMCallResult


class AnthropicProvider(BaseLLMProvider):
    """Claude provider via the Anthropic SDK."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 1024,
    ) -> None:
        # Lazy import to avoid hard dependency in tests
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    async def chat(self, messages: list[dict]) -> LLMCallResult:
        start = time.monotonic()
        try:
            # Separate system message from user/assistant messages
            system_text = ""
            chat_messages: list[dict] = []
            for msg in messages:
                if msg.get("role") == "system":
                    system_text = msg["content"]
                else:
                    chat_messages.append(msg)

            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": chat_messages,
                "max_tokens": self.max_tokens,
            }
            if system_text:
                kwargs["system"] = system_text

            response = await self.client.messages.create(**kwargs)
            latency = (time.monotonic() - start) * 1000
            return LLMCallResult(
                text=response.content[0].text,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=(
                    response.usage.input_tokens + response.usage.output_tokens
                ),
                latency_ms=latency,
                status="success",
                provider_name="anthropic",
                model_name=self.model,
            )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return LLMCallResult(
                text="",
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                latency_ms=latency,
                status="error",
                error_message=str(e),
                provider_name="anthropic",
                model_name=self.model,
            )

    def get_provider_name(self) -> str:
        return "anthropic"
