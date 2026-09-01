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
    database_url: str = "postgresql+psycopg://careeros@localhost:5432/careeros"
    cors_origins: str = "http://localhost:8081,http://localhost:19006"
    static_directory: str | None = None
    ai_mode: Literal["fixture", "live", "auto"] = "fixture"
    ai_provider: str = "openai"
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-5.6-terra"
    ai_critic_model: str | None = None
    ai_repair_model: str | None = None
    ai_discovery_model: str | None = None
    ai_response_format: Literal["json_schema", "json_object"] = "json_schema"
    ai_reasoning_effort: Literal["low", "medium", "high"] | None = None
    ai_request_timeout_seconds: float = Field(default=60.0, ge=10.0, le=180.0)
    ai_max_completion_tokens: int = Field(default=5000, ge=512, le=131072)
    ai_critic_max_completion_tokens: int = Field(default=1600, ge=256, le=32768)
    ai_repair_max_completion_tokens: int = Field(default=4800, ge=512, le=131072)
    ai_discovery_max_completion_tokens: int = Field(default=700, ge=256, le=8192)
    ai_transient_retry_attempts: int = Field(default=1, ge=0, le=2)
    ai_transient_retry_delay_seconds: float = Field(default=15.0, ge=1.0, le=60.0)
    ai_max_repair_attempts: int = Field(default=1, ge=0, le=3)
    ai_quality_threshold: int = Field(default=80, ge=60, le=100)
    ai_generation_limit_per_hour: int = Field(default=3, ge=1, le=100)
    ai_global_generation_limit_per_hour: int = Field(default=12, ge=1, le=1000)
    resource_request_timeout_seconds: float = Field(default=4.0, ge=1.0, le=15.0)
    resource_max_results_per_step: int = Field(default=3, ge=1, le=6)
    resource_cache_ttl_hours: int = Field(default=168, ge=1, le=720)
    resource_alternate_limit_per_step_per_day: int = Field(default=3, ge=1, le=20)
    resource_alternate_cooldown_seconds: int = Field(default=12, ge=0, le=300)
    google_web_client_id: str = ""
    google_ios_client_id: str = ""
    google_android_client_id: str = ""
    apple_client_ids: str = ""
    auth_anonymous_limit_per_15_minutes: int = Field(default=120, ge=10, le=5000)
    auth_identity_limit_per_15_minutes: int = Field(default=20, ge=5, le=200)
    auth_deletion_limit_per_15_minutes: int = Field(default=5, ge=1, le=50)
    ai_api_key: SecretStr | None = None
    youtube_api_key: SecretStr | None = None
    brave_search_api_key: SecretStr | None = None

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

    @field_validator(
        "ai_model", "ai_critic_model", "ai_repair_model", "ai_discovery_model", mode="before"
    )
    @classmethod
    def validate_ai_model(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("AI model must be a string identifier")
        normalized = value.strip()
        if not normalized:
            return None
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,119}", normalized):
            raise ValueError("AI model must be a safe provider model identifier")
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

    @field_validator(
        "google_web_client_id",
        "google_ios_client_id",
        "google_android_client_id",
        "apple_client_ids",
        mode="before",
    )
    @classmethod
    def normalize_oauth_client_ids(cls, value: object) -> object:
        if not isinstance(value, str):
            raise ValueError("OAuth client identifiers must be strings")
        normalized = ",".join(item.strip() for item in value.split(",") if item.strip())
        if normalized and not re.fullmatch(r"[A-Za-z0-9._,:/-]{3,1000}", normalized):
            raise ValueError("OAuth client identifiers contain unsupported characters")
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
    def youtube_api_configured(self) -> bool:
        return bool(
            self.youtube_api_key is not None and self.youtube_api_key.get_secret_value().strip()
        )

    @property
    def brave_search_api_configured(self) -> bool:
        return bool(
            self.brave_search_api_key is not None
            and self.brave_search_api_key.get_secret_value().strip()
        )

    @property
    def google_client_ids(self) -> list[str]:
        return list(
            dict.fromkeys(
                value
                for value in (
                    self.google_web_client_id,
                    self.google_ios_client_id,
                    self.google_android_client_id,
                )
                if value
            )
        )

    @property
    def allowed_apple_client_ids(self) -> list[str]:
        return [value for value in self.apple_client_ids.split(",") if value]

    @property
    def resolved_ai_critic_model(self) -> str:
        return self.ai_critic_model or self.ai_model

    @property
    def resolved_ai_repair_model(self) -> str:
        return self.ai_repair_model or self.ai_model

    @property
    def resolved_ai_discovery_model(self) -> str:
        return self.ai_discovery_model or self.ai_model

    @property
    def ai_generation_mode(self) -> Literal["live_ai", "deterministic_preview", "misconfigured"]:
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
