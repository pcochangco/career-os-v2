from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    roadmap_generation: Literal["live_ai", "deterministic_preview", "misconfigured"]
    ai_provider: str | None
    ai_model: str | None
    fallback_enabled: bool


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        roadmap_generation=settings.ai_generation_mode,
        ai_provider=(
            settings.ai_provider if settings.ai_generation_mode == "live_ai" else None
        ),
        ai_model=settings.ai_model if settings.ai_generation_mode == "live_ai" else None,
        fallback_enabled=settings.ai_mode == "auto",
    )
