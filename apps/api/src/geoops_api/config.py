"""Validated runtime configuration for the API service."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SEED_DATA_PATH = Path(__file__).resolve().parents[4] / "data/seed/geoops_seed.json"


class Settings(BaseSettings):
    """Environment-backed settings with safe local defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    seed_data_path: Path = DEFAULT_SEED_DATA_PATH

    service_name: str = "geoops-api"
    version: str = "0.1.0"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""

    return Settings()
