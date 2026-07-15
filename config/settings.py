"""Application settings.

Settings are loaded from environment variables (prefixed ``VA_``) and an
optional ``.env`` file at the project root. A single cached :class:`Settings`
instance is exposed via :func:`get_settings` and injected throughout the app.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Strongly-typed application configuration.

    Every field maps to a ``VA_``-prefixed environment variable, e.g.
    ``VA_OPENAI_API_KEY`` populates :attr:`openai_api_key`.
    """

    model_config = SettingsConfigDict(
        env_prefix="VA_",
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- OpenAI ----
    openai_api_key: str = Field(default="", description="OpenAI API key.")
    llm_model: str = Field(default="gpt-5")
    realtime_model: str = Field(default="gpt-4o-realtime-preview")
    stt_model: str = Field(default="whisper-1")
    tts_model: str = Field(default="gpt-4o-mini-tts")
    tts_voice: str = Field(default="alloy")
    vision_model: str = Field(default="gpt-5")

    # ---- Voice ----
    wake_words: list[str] = Field(default_factory=lambda: ["hey assistant", "jarvis"])
    enable_wake_word: bool = True
    silence_timeout_ms: int = 1200
    sample_rate: int = 16000

    # ---- GUI ----
    theme: str = "dark"
    animation_speed: float = 1.0
    accent_color: str = "#22d3ee"

    # ---- Agent ----
    max_agent_steps: int = 12
    enable_automation: bool = True
    confirm_destructive: bool = True

    # ---- Storage ----
    db_path: str = "database/voice_agent.db"
    log_dir: str = "logs"
    log_level: str = "INFO"

    # ---- Backend ----
    api_host: str = "127.0.0.1"
    api_port: int = 8765

    @field_validator("wake_words", mode="before")
    @classmethod
    def _split_wake_words(cls, value: object) -> object:
        """Allow ``VA_WAKE_WORDS`` to be a comma-separated string."""
        if isinstance(value, str):
            return [w.strip().lower() for w in value.split(",") if w.strip()]
        return value

    @property
    def db_file(self) -> Path:
        """Absolute path to the SQLite database file."""
        path = Path(self.db_path)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def log_path(self) -> Path:
        """Absolute path to the log directory."""
        path = Path(self.log_dir)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def has_openai(self) -> bool:
        """Whether a usable OpenAI API key is configured."""
        return bool(self.openai_api_key and self.openai_api_key.startswith("sk-"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide cached :class:`Settings` instance."""
    return Settings()
