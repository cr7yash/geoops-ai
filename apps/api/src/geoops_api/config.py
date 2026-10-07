"""Validated runtime configuration for the API service."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SEED_DATA_PATH = Path(__file__).resolve().parents[4] / "data/seed/geoops_seed.json"
DEFAULT_KNOWLEDGE_DOCUMENTS_PATH = Path(__file__).resolve().parents[4] / "data/documents"


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
    maps_provider: Literal["mock", "google"] = "mock"
    google_maps_api_key: SecretStr | None = None
    maps_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    knowledge_documents_path: Path = DEFAULT_KNOWLEDGE_DOCUMENTS_PATH
    embedding_dimensions: int = Field(default=256, ge=16, le=1024)
    knowledge_chunk_size: int = Field(default=900, ge=200, le=4000)
    knowledge_chunk_overlap: int = Field(default=120, ge=0, le=500)
    model_provider: Literal["local", "gemini_api", "vertex_ai"] = "local"
    model_name: str = "geoops-local-planner-v1"
    gemini_api_key: SecretStr | None = None
    google_cloud_project: str | None = None
    google_cloud_location: str = "us-central1"
    approval_store: Literal["memory", "firestore"] = "memory"
    approval_ttl_minutes: int = Field(default=30, ge=5, le=1440)
    firestore_approvals_collection: str = "approval_requests"

    service_name: str = "geoops-api"
    version: str = "0.1.0"

    @model_validator(mode="after")
    def validate_maps_configuration(self) -> "Settings":
        if self.maps_provider == "google" and (
            self.google_maps_api_key is None
            or not self.google_maps_api_key.get_secret_value().strip()
        ):
            raise ValueError("GOOGLE_MAPS_API_KEY is required when MAPS_PROVIDER=google")
        if self.model_provider == "gemini_api" and (
            self.gemini_api_key is None or not self.gemini_api_key.get_secret_value().strip()
        ):
            raise ValueError("GEMINI_API_KEY is required when MODEL_PROVIDER=gemini_api")
        if (self.model_provider == "vertex_ai" or self.approval_store == "firestore") and not (
            self.google_cloud_project and self.google_cloud_project.strip()
        ):
            raise ValueError("GOOGLE_CLOUD_PROJECT is required for Vertex AI or Firestore")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""

    return Settings()
