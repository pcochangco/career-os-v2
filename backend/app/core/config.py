from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CAREEROS_",
        extra="ignore",
        frozen=True,
    )

    app_name: str = "CareerOS API"
    app_version: str = "0.1.0"
    environment: str = "local"
    database_url: str = "postgresql+psycopg://careeros:careeros_local@localhost:5432/careeros"
    cors_origins: str = "http://localhost:8081,http://localhost:19006"
    static_directory: str | None = None
    ai_provider: Literal["fixture", "openai", "auto"] = "fixture"
    ai_model: str = "gpt-5.6-terra"
    ai_reasoning_effort: Literal["low", "medium", "high"] = "medium"
    ai_request_timeout_seconds: float = Field(default=60.0, ge=10.0, le=180.0)
    ai_max_repair_attempts: int = Field(default=1, ge=0, le=3)
    ai_quality_threshold: int = Field(default=80, ge=60, le=100)
    ai_generation_limit_per_hour: int = Field(default=3, ge=1, le=100)
    ai_global_generation_limit_per_hour: int = Field(default=12, ge=1, le=1000)
    resource_request_timeout_seconds: float = Field(default=4.0, ge=1.0, le=15.0)
    resource_max_results_per_step: int = Field(default=3, ge=1, le=6)
    openai_api_key: SecretStr | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: object) -> object:
        if isinstance(value, str) and value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def openai_configured(self) -> bool:
        return bool(
            self.openai_api_key is not None
            and self.openai_api_key.get_secret_value().strip()
        )

    @property
    def ai_generation_mode(self) -> Literal[
        "live_ai", "deterministic_preview", "misconfigured"
    ]:
        if self.ai_provider == "fixture":
            return "deterministic_preview"
        if self.openai_configured:
            return "live_ai"
        if self.ai_provider == "auto":
            return "deterministic_preview"
        return "misconfigured"


@lru_cache
def get_settings() -> Settings:
    return Settings()
