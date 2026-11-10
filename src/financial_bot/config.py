"""App settings, loaded from environment variables (and `.env`)."""

from datetime import date, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: SecretStr
    database_url: str = "sqlite:///data/expenses.db"
    chat_model: str = "openai:gpt-5-nano"
    transcribe_model: str = "gpt-4o-mini-transcribe"
    timezone: str = "America/Sao_Paulo"


@lru_cache
def get_settings() -> Settings:
    # Fields come from the environment; pyright doesn't know pydantic-settings does that.
    return Settings()  # pyright: ignore[reportCallIssue]


@lru_cache
def get_timezone() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def today() -> date:
    """Today's date in the configured timezone (not the server's)."""
    return datetime.now(get_timezone()).date()
