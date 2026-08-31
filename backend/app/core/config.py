import re
from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

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
    ai_mode: Literal["fixture", "live", "auto"] = "fixture"
    ai_provider: str = "openai"
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-5.6-terra"
    ai_response_format: Literal["json_schema", "json_object"] = "json_schema"
    ai_reasoning_effort: Literal["low", "medium", "high"] | None = None
    ai_request_timeout_seconds: float = Field(default=60.0, ge=10.0, le=180.0)
    ai_max_completion_tokens: int = Field(default=8000, ge=512, le=131072)
    ai_max_repair_attempts: int = Field(default=1, ge=0, le=3)
    ai_quality_threshold: int = Field(default=80, ge=60, le=100)
    ai_generation_limit_per_hour: int = Field(default=3, ge=1, le=100)
    ai_global_generation_limit_per_hour: int = Field(default=12, ge=1, le=1000)
    resource_request_timeout_seconds: float = Field(default=4.0, ge=1.0, le=15.0)
    resource_max_results_per_step: int = Field(default=3, ge=1, le=6)
    ai_api_key: SecretStr | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: object) -> object:
        if isinstance(value, str) and value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @field_validator("ai_provider")
    @classmethod
    def validate_ai_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,23}", normalized):
            raise ValueError("AI provider must be a lowercase identifier")
        return normalized

    @field_validator("ai_base_url")
    @classmethod
    def validate_ai_base_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        parsed = urlsplit(normalized)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("AI base URL must be a credential-free HTTPS endpoint")
        return normalized

    @field_validator("ai_reasoning_effort", mode="before")
    @classmethod
    def use_optional_reasoning_effort(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def ai_configured(self) -> bool:
        return bool(self.ai_api_key is not None and self.ai_api_key.get_secret_value().strip())

    @property
    def ai_generation_mode(self) -> Literal[
        "live_ai", "deterministic_preview", "misconfigured"
    ]:
        if self.ai_mode == "fixture":
            return "deterministic_preview"
        if self.ai_configured:
            return "live_ai"
        if self.ai_mode == "auto":
            return "deterministic_preview"
        return "misconfigured"


@lru_cache
def get_settings() -> Settings:
    return Settings()
