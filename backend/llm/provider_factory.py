"""Factory for creating LLM provider instances."""
from __future__ import annotations

from backend.llm.base_provider import BaseLLMProvider


class ProviderFactory:
    """Registry and factory for LLM providers."""

    _registry: dict[str, type[BaseLLMProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[BaseLLMProvider]) -> None:
        cls._registry[name] = provider_class

    @classmethod
    def create(cls, provider_name: str, **kwargs) -> BaseLLMProvider:
        if provider_name not in cls._registry:
            raise ValueError(
                f"Unknown provider '{provider_name}'. "
                f"Available: {list(cls._registry.keys())}"
            )
        return cls._registry[provider_name](**kwargs)

    @classmethod
    def available_providers(cls) -> list[str]:
        return list(cls._registry.keys())


def _register_defaults() -> None:
    """Register built-in providers. Called at module load time."""
    from backend.llm.anthropic_provider import AnthropicProvider
    ProviderFactory.register("anthropic", AnthropicProvider)


_register_defaults()
