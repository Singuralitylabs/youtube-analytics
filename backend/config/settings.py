"""Environment-driven configuration via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    YOUTUBE_API_KEY: str = ""
    CHANNEL_ID: str = ""
    CLIENT_SECRETS_FILE: str = "client_secrets.json"
    TOKEN_FILE: str = "token.json"
    SPREADSHEET_ID: str = ""
    FRONTEND_URL: str = "http://localhost:3000"

    # ---- Monthly report generation ----
    # Google Gemini API key (free tier) used to author the interpretive sections.
    GEMINI_API_KEY: str = ""
    # Gemini model id (Flash is free-tier friendly; configurable for quality).
    GEMINI_MODEL: str = "gemini-2.5-flash"
    # Slack Incoming Webhook URL for the monthly notification.
    SLACK_WEBHOOK_URL: str = ""
    # Directory the report Markdown is written to (relative to the repo root).
    REPORT_OUTPUT_DIR: str = "reports"
    # Repo slug and branch used to build the report's GitHub blob URL.
    GITHUB_REPO: str = "Singuralitylabs/youtube-analytics"
    GITHUB_BRANCH: str = "main"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton `Settings` instance."""
    return Settings()
