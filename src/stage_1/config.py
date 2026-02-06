"""Configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Mistral AI
    mistral_api_key: str

    # Langfuse
    langfuse_secret_key: str
    langfuse_public_key: str
    langfuse_base_url: str = "https://us.cloud.langfuse.com"


def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()  # type: ignore[missing-argument]  # args loaded from env
