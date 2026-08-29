from functools import lru_cache

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

@lru_cache
def get_settings() -> Settings:
    return Settings()
