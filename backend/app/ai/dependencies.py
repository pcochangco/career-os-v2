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


def live_service(settings: Settings) -> RoadmapGenerationService:
    api_key = settings.ai_api_key
    if api_key is None or not api_key.get_secret_value().strip():
        raise RoadmapProviderError("Live AI is selected but no API key is configured")

    from app.ai.providers.compatible import OpenAICompatibleRoadmapProvider

    provider = OpenAICompatibleRoadmapProvider(
        provider_name=settings.ai_provider,
        api_key=api_key.get_secret_value(),
        base_url=settings.ai_base_url,
        model=settings.ai_model,
        response_format_mode=settings.ai_response_format,
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
    if settings.ai_mode == "fixture":
        return fallback
    if settings.ai_mode == "live":
        return live_service(settings)
    if settings.ai_mode == "auto":
        if not settings.ai_configured:
            return fallback
        return FallbackRoadmapGenerationService(
            primary=live_service(settings),
            fallback=fallback,
        )
    raise RoadmapProviderError(f"Unsupported AI mode: {settings.ai_mode}")


def get_generation_service() -> RoadmapGenerationService | FallbackRoadmapGenerationService:
    settings = get_settings()
    return create_generation_service(settings)


GenerationService = Annotated[
    RoadmapGenerationService | FallbackRoadmapGenerationService,
    Depends(get_generation_service),
]
