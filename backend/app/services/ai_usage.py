"""Bounded, privacy-safe accounting for operations that may use an AI provider."""

import re
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.providers.base import ProviderResult
from app.core.config import Settings
from app.db.models import AIUsageEvent, User

GOAL_INTENT_OPERATION = "goal_intent"
DISCOVERY_OPERATION = "discovery_question"
ROADMAP_OPERATION = "roadmap_generation"

_SAFE_FAILURE_CODE = re.compile(r"[a-zA-Z0-9._;=/-]{1,160}")


def live_ai_requested(settings: Settings) -> bool:
    return settings.ai_mode == "live" or (settings.ai_mode == "auto" and settings.ai_configured)


def operation_limits(settings: Settings, operation: str) -> tuple[int, int]:
    if operation == GOAL_INTENT_OPERATION:
        return settings.ai_goal_intent_limit_per_hour, settings.ai_global_goal_intent_limit_per_hour
    if operation == DISCOVERY_OPERATION:
        return settings.ai_discovery_limit_per_hour, settings.ai_global_discovery_limit_per_hour
    if operation == ROADMAP_OPERATION:
        return settings.ai_generation_limit_per_hour, settings.ai_global_generation_limit_per_hour
    raise ValueError(f"Unsupported AI operation: {operation}")


def start_ai_usage_event(
    db: Session,
    *,
    user: User,
    operation: str,
    goal_id: UUID | None,
    settings: Settings,
) -> tuple[AIUsageEvent, bool]:
    """Reserve one bounded live operation; quota exhaustion uses the local fixture instead."""
    use_live_provider = live_ai_requested(settings)
    use_quota_fallback = False
    if use_live_provider:
        user_limit, global_limit = operation_limits(settings, operation)
        window_start = datetime.now(UTC) - timedelta(hours=1)
        usage_filter = (
            AIUsageEvent.operation == operation,
            AIUsageEvent.created_at >= window_start,
            AIUsageEvent.requested_provider != "fixture",
        )
        user_count = db.scalar(
            select(func.count(AIUsageEvent.id)).where(
                AIUsageEvent.user_id == user.id,
                *usage_filter,
            )
        )
        global_count = db.scalar(select(func.count(AIUsageEvent.id)).where(*usage_filter))
        use_quota_fallback = (user_count or 0) >= user_limit or (global_count or 0) >= global_limit

    requested_provider = (
        "fixture" if not use_live_provider or use_quota_fallback else settings.ai_provider
    )
    event = AIUsageEvent(
        user_id=user.id,
        goal_id=goal_id,
        operation=operation,
        requested_provider=requested_provider,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event, use_quota_fallback


def finish_ai_usage_event(
    db: Session,
    event: AIUsageEvent,
    *,
    outcome: str,
    result: ProviderResult[object] | None = None,
    provider_source: str = "",
    provider_model: str = "",
    duration_started_at: float | None = None,
    failure: Exception | None = None,
) -> None:
    event.outcome = outcome
    event.resulting_source = provider_source
    event.provider_model = provider_model
    if result is not None:
        event.input_tokens = result.input_tokens
        event.output_tokens = result.output_tokens
        event.response_count = 1 if result.response_id else 0
    if duration_started_at is not None:
        event.duration_ms = round((perf_counter() - duration_started_at) * 1000)
    event.failure_code = safe_failure_code(failure) if failure is not None else ""
    event.completed_at = datetime.now(UTC)
    db.commit()


def safe_failure_code(error: Exception) -> str:
    candidate = str(getattr(error, "diagnostic_code", type(error).__name__)).strip()
    return candidate if _SAFE_FAILURE_CODE.fullmatch(candidate) else type(error).__name__
