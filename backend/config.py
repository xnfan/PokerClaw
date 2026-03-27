"""Global configuration for PokerClaw backend."""
import os
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    default_provider: str = "anthropic"
    default_model: str = "claude-sonnet-4-20250514"
    decision_timeout_seconds: float = 30.0
    max_retry_on_error: int = 1
    max_tokens: int = 1024


@dataclass
class GameConfig:
    min_players: int = 2
    max_players: int = 9
    default_small_blind: int = 50
    default_big_blind: int = 100
    default_buy_in: int = 10000
    human_action_timeout_seconds: float = 60.0


@dataclass
class AppConfig:
    db_url: str = field(
        default_factory=lambda: os.getenv(
            "POKERCLAW_DB_URL", "sqlite:///pokerclaw.db"
        )
    )
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    llm: LLMConfig = field(default_factory=LLMConfig)
    game: GameConfig = field(default_factory=GameConfig)


# Singleton config instance
app_config = AppConfig()
