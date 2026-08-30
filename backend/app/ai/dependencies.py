from typing import Annotated

from fastapi import Depends

from app.ai.providers.base import RoadmapProviderError
from app.ai.providers.fixture import FixtureRoadmapProvider
from app.ai.service import FallbackRoadmapGenerationService, RoadmapGenerationService
from app.core.config import Settings, get_settings


def fixture_service(settings: Settings) -> RoadmapGenerationService:
    return RoadmapGenerationService(
        provider=FixtureRoadmapProvider(),
        quality_threshold=settings.ai_quality_threshold,
        max_repair_attempts=settings.ai_max_repair_attempts,
    )


def openai_service(settings: Settings) -> RoadmapGenerationService:
    api_key = settings.openai_api_key
    if api_key is None or not api_key.get_secret_value().strip():
        raise RoadmapProviderError("OpenAI is selected but no API key is configured")

    from app.ai.providers.openai import OpenAIRoadmapProvider

    provider = OpenAIRoadmapProvider(
        api_key=api_key.get_secret_value(),
        model=settings.ai_model,
        reasoning_effort=settings.ai_reasoning_effort,
        timeout_seconds=settings.ai_request_timeout_seconds,
    )
    return RoadmapGenerationService(
        provider=provider,
        quality_threshold=settings.ai_quality_threshold,
        max_repair_attempts=settings.ai_max_repair_attempts,
    )


def create_generation_service(
    settings: Settings,
) -> RoadmapGenerationService | FallbackRoadmapGenerationService:
    fallback = fixture_service(settings)
    if settings.ai_provider == "fixture":
        return fallback
    if settings.ai_provider == "openai":
        return openai_service(settings)
    if settings.ai_provider == "auto":
        if not settings.openai_configured:
            return fallback
        return FallbackRoadmapGenerationService(
            primary=openai_service(settings),
            fallback=fallback,
        )
    raise RoadmapProviderError(f"Unsupported AI provider: {settings.ai_provider}")


def get_generation_service() -> RoadmapGenerationService | FallbackRoadmapGenerationService:
    settings = get_settings()
    return create_generation_service(settings)


GenerationService = Annotated[
    RoadmapGenerationService | FallbackRoadmapGenerationService,
    Depends(get_generation_service),
]
