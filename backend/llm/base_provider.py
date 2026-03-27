"""Base LLM provider interface with metrics-aware response."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMCallResult:
    """Result of a single LLM API call, carrying both text and metrics."""
    text: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: float
    status: str  # "success" / "error" / "timeout"
    error_message: str | None = None
    provider_name: str = ""
    model_name: str = ""


class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers. All providers must return LLMCallResult."""

    @abstractmethod
    async def chat(self, messages: list[dict]) -> LLMCallResult:
        """Send messages and return result with metrics."""
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        ...
