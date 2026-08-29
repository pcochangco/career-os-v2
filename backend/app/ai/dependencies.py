from typing import Annotated

from fastapi import Depends

from app.ai.providers.base import RoadmapProviderError
from app.ai.providers.fixture import FixtureRoadmapProvider
from app.ai.service import RoadmapGenerationService
from app.core.config import get_settings


def get_generation_service() -> RoadmapGenerationService:
    settings = get_settings()
    if settings.ai_provider == "fixture":
        provider = FixtureRoadmapProvider()
    elif settings.ai_provider == "openai":
        from app.ai.providers.openai import OpenAIRoadmapProvider

        if (
            settings.openai_api_key is None
            or not settings.openai_api_key.get_secret_value().strip()
        ):
            raise RoadmapProviderError("OpenAI is selected but no API key is configured")
        provider = OpenAIRoadmapProvider(
            api_key=settings.openai_api_key.get_secret_value(),
            model=settings.ai_model,
            reasoning_effort=settings.ai_reasoning_effort,
        )
    else:
        raise RoadmapProviderError(f"Unsupported AI provider: {settings.ai_provider}")

    return RoadmapGenerationService(
        provider=provider,
        quality_threshold=settings.ai_quality_threshold,
        max_repair_attempts=settings.ai_max_repair_attempts,
    )


GenerationService = Annotated[RoadmapGenerationService, Depends(get_generation_service)]
