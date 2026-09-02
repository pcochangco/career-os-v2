from typing import Annotated

from fastapi import Depends

from app.ai.providers.base import RoadmapProviderError
from app.ai.providers.fixture import FixtureRoadmapProvider
from app.ai.service import (
    FallbackRoadmapGenerationService,
    RetryingRoadmapGenerationService,
    RoadmapGenerationService,
)
from app.core.config import Settings, get_settings
from app.discovery.service import AdaptiveDiscoveryService, FixtureDiscoveryProvider


def fixture_service(settings: Settings) -> RoadmapGenerationService:
    return RoadmapGenerationService(
        provider=FixtureRoadmapProvider(),
        quality_threshold=settings.ai_quality_threshold,
        max_repair_attempts=settings.ai_max_repair_attempts,
    )


def live_service(settings: Settings) -> RetryingRoadmapGenerationService:
    api_key = settings.ai_api_key
    if api_key is None or not api_key.get_secret_value().strip():
        raise RoadmapProviderError("Live AI is selected but no API key is configured")

    from app.ai.providers.compatible import OpenAICompatibleRoadmapProvider

    provider = OpenAICompatibleRoadmapProvider(
        provider_name=settings.ai_provider,
        api_key=api_key.get_secret_value(),
        base_url=settings.ai_base_url,
        model=settings.ai_model,
        critic_model=settings.resolved_ai_critic_model,
        repair_model=settings.resolved_ai_repair_model,
        discovery_model=settings.resolved_ai_discovery_model,
        response_format_mode=settings.ai_response_format,
        reasoning_effort=settings.ai_reasoning_effort,
        timeout_seconds=settings.ai_request_timeout_seconds,
        max_completion_tokens=settings.ai_max_completion_tokens,
        critic_max_completion_tokens=settings.ai_critic_max_completion_tokens,
        repair_max_completion_tokens=settings.ai_repair_max_completion_tokens,
        discovery_max_completion_tokens=settings.ai_discovery_max_completion_tokens,
    )
    return RetryingRoadmapGenerationService(
        RoadmapGenerationService(
            provider=provider,
            quality_threshold=settings.ai_quality_threshold,
            max_repair_attempts=settings.ai_max_repair_attempts,
        ),
        max_transient_retries=settings.ai_transient_retry_attempts,
        retry_delay_seconds=settings.ai_transient_retry_delay_seconds,
    )


def create_generation_service(
    settings: Settings,
) -> RoadmapGenerationService | RetryingRoadmapGenerationService | FallbackRoadmapGenerationService:
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


def get_discovery_service() -> AdaptiveDiscoveryService:
    settings = get_settings()
    if settings.ai_mode == "fixture":
        return AdaptiveDiscoveryService(FixtureDiscoveryProvider())
    if not settings.ai_configured:
        if settings.ai_mode == "auto":
            return AdaptiveDiscoveryService(FixtureDiscoveryProvider())
        raise RoadmapProviderError("Live AI is selected but no API key is configured")

    from app.ai.providers.compatible import OpenAICompatibleRoadmapProvider

    api_key = settings.ai_api_key
    if api_key is None:
        raise RoadmapProviderError("Live AI is selected but no API key is configured")
    provider = OpenAICompatibleRoadmapProvider(
        provider_name=settings.ai_provider,
        api_key=api_key.get_secret_value(),
        base_url=settings.ai_base_url,
        model=settings.ai_model,
        critic_model=settings.resolved_ai_critic_model,
        repair_model=settings.resolved_ai_repair_model,
        discovery_model=settings.resolved_ai_discovery_model,
        response_format_mode=settings.ai_response_format,
        reasoning_effort=settings.ai_reasoning_effort,
        timeout_seconds=settings.ai_request_timeout_seconds,
        max_completion_tokens=settings.ai_max_completion_tokens,
        critic_max_completion_tokens=settings.ai_critic_max_completion_tokens,
        repair_max_completion_tokens=settings.ai_repair_max_completion_tokens,
        discovery_max_completion_tokens=settings.ai_discovery_max_completion_tokens,
    )
    return AdaptiveDiscoveryService(provider)


def get_goal_intent_service() -> AdaptiveDiscoveryService:
    return get_discovery_service()


GenerationService = Annotated[
    RoadmapGenerationService | RetryingRoadmapGenerationService | FallbackRoadmapGenerationService,
    Depends(get_generation_service),
]

DiscoveryService = Annotated[AdaptiveDiscoveryService, Depends(get_discovery_service)]
GoalIntentService = Annotated[AdaptiveDiscoveryService, Depends(get_goal_intent_service)]
