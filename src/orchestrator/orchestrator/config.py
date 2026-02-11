"""Application configuration via pydantic-settings.

Reads from environment variables and .env file at project root.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root is 4 levels up from this file:
# src/orchestrator/orchestrator/config.py -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---
    mistral_api_key: str
    mistral_model: str = "mistral-small-latest"
    mistral_temperature: float = 0.0

    # --- Menu ---
    menu_json_path: str = str(
        PROJECT_ROOT
        / "menus"
        / "mcdonalds"
        / "breakfast-menu"
        / "json"
        / "breakfast-v2.json"
    )

    # --- Logging ---
    log_level: str = "DEBUG"

    # --- Langfuse ---
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance (created once)."""
    return Settings()
