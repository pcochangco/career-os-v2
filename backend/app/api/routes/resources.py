from datetime import UTC, datetime, timedelta
from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentUser, DbSession
from app.api.routes.progress import get_owned_active_step
from app.api.routes.roadmaps import get_owned_roadmap
from app.api.schemas import LearningResourceRead, StepResourcesRead
from app.core.config import get_settings
from app.db.models import (
    RoadmapStepResource,
    RoadmapStepResourceFeedback,
    RoadmapStepResourceRefreshAttempt,
)
from app.resources.dependencies import get_resource_resolver
from app.resources.service import ResourceResolver
from app.services.progress import calculate_roadmap_progress

router = APIRouter(prefix="/roadmap-steps", tags=["resources"])
Resolver = Annotated[ResourceResolver, Depends(get_resource_resolver)]


def read_cached_resources(db: DbSession, step_id: UUID) -> list[RoadmapStepResource]:
    return list(
        db.scalars(
            select(RoadmapStepResource)
            .where(RoadmapStepResource.step_id == step_id)
            .order_by(RoadmapStepResource.created_at, RoadmapStepResource.id)
        ).all()
    )


def read_rejected_resource_urls(db: DbSession, *, user_id: UUID, step_id: UUID) -> set[str]:
    return set(
        db.scalars(
            select(RoadmapStepResourceFeedback.resource_url).where(
                RoadmapStepResourceFeedback.user_id == user_id,
                RoadmapStepResourceFeedback.step_id == step_id,
            )
        ).all()
    )


def to_resource_response(
    step_id: UUID,
    resources: list[RoadmapStepResource],
    *,
    cached: bool,
) -> StepResourcesRead:
    return StepResourcesRead(
        step_id=step_id,
        resources=[LearningResourceRead.model_validate(resource) for resource in resources],
        available=bool(resources),
        cached=cached,
        message=(
            ""
            if resources
            else "No resources could be verified right now. You can try again later."
        ),
    )


def remove_irrelevant_cached_resources(
    db: DbSession,
    resolver: ResourceResolver,
    resources: list[RoadmapStepResource],
    queries: list[str],
) -> bool:
    removed = False
    for resource in resources:
        if resolver.is_cached_resource_acceptable(
            provider=resource.provider,
            verified_at=resource.verified_at,
            title=resource.title,
            description=resource.description,
            queries=queries,
        ):
            continue
        db.delete(resource)
        removed = True
    if removed:
        db.commit()
    return removed


def visible_resources(
    resources: list[RoadmapStepResource],
    rejected_urls: set[str],
) -> list[RoadmapStepResource]:
    """Hide rejected recommendations without destroying the row needed for Undo."""
    return [resource for resource in resources if resource.url not in rejected_urls]


def start_resource_refresh_attempt(
    db: DbSession,
    *,
    user_id: UUID,
    step_id: UUID,
) -> None:
    settings = get_settings()
    now = datetime.now(UTC)
    daily_window_start = now - timedelta(days=1)
    attempts = db.scalar(
        select(func.count(RoadmapStepResourceRefreshAttempt.id)).where(
            RoadmapStepResourceRefreshAttempt.user_id == user_id,
            RoadmapStepResourceRefreshAttempt.step_id == step_id,
            RoadmapStepResourceRefreshAttempt.created_at >= daily_window_start,
        )
    )
    if (attempts or 0) >= settings.resource_alternate_limit_per_step_per_day:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="You have reached this step's alternate-resource limit. Try another step later.",
            headers={"Retry-After": "86400"},
        )
    latest_attempt = db.scalar(
        select(RoadmapStepResourceRefreshAttempt)
        .where(
            RoadmapStepResourceRefreshAttempt.user_id == user_id,
            RoadmapStepResourceRefreshAttempt.step_id == step_id,
        )
        .order_by(RoadmapStepResourceRefreshAttempt.created_at.desc())
        .limit(1)
    )
    if latest_attempt is not None and settings.resource_alternate_cooldown_seconds:
        latest_created_at = latest_attempt.created_at
        if latest_created_at.tzinfo is None:
            latest_created_at = latest_created_at.replace(tzinfo=UTC)
        elapsed = (now - latest_created_at).total_seconds()
        remaining = settings.resource_alternate_cooldown_seconds - elapsed
        if remaining > 0:
            retry_after = max(1, ceil(remaining))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {retry_after} seconds before finding another resource set.",
                headers={"Retry-After": str(retry_after)},
            )
    db.add(RoadmapStepResourceRefreshAttempt(user_id=user_id, step_id=step_id))
    db.commit()


@router.post("/{step_id}/resources/resolve", response_model=StepResourcesRead)
def resolve_step_resources(
    step_id: UUID,
    user: CurrentUser,
    db: DbSession,
    resolver: Resolver,
    refresh: bool = False,
) -> StepResourcesRead:
    step, roadmap, _ = get_owned_active_step(db, user, step_id)
    owned_roadmap = get_owned_roadmap(db, user, roadmap.id)
    if calculate_roadmap_progress(db, user, owned_roadmap).current_step_id != step.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resources are available when this step becomes current",
        )

    if refresh:
        start_resource_refresh_attempt(db, user_id=user.id, step_id=step.id)

    rejected_urls = read_rejected_resource_urls(db, user_id=user.id, step_id=step.id)
    all_cached = read_cached_resources(db, step.id)
    cached = visible_resources(all_cached, rejected_urls)
    cache_changed = remove_irrelevant_cached_resources(
        db,
        resolver,
        cached,
        step.resource_queries,
    )
    if cache_changed:
        all_cached = read_cached_resources(db, step.id)
        cached = visible_resources(all_cached, rejected_urls)
    excluded_urls = set(rejected_urls)
    if refresh:
        excluded_urls.update(resource.url for resource in cached)
    # Refresh pre-video-first caches once. This makes the new recommendation policy
    # useful immediately instead of waiting for the old seven-day cache window.
    needs_primary_video = resolver.has_video_provider and (
        not cached or cached[0].resource_type != "video"
    )
    if cached and not cache_changed and not needs_primary_video and not refresh:
        return to_resource_response(step.id, cached, cached=True)

    if needs_primary_video or refresh or cache_changed:
        for resource in cached:
            db.delete(resource)
        db.commit()
        cached = []

    candidates = resolver.resolve(step.resource_queries, excluded_urls=excluded_urls)
    existing_urls = {resource.url for resource in read_cached_resources(db, step.id)}
    resources = [
        RoadmapStepResource(
            step_id=step.id,
            provider=candidate.provider,
            resource_type=candidate.resource_type,
            title=candidate.title,
            url=candidate.url,
            source_name=candidate.source_name,
            description=candidate.description,
            why_relevant=candidate.why_relevant,
            thumbnail_url=candidate.thumbnail_url,
            verified_at=candidate.verified_at,
        )
        for candidate in candidates
        if candidate.url not in existing_urls
    ]
    db.add_all(resources)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    resolved = visible_resources(read_cached_resources(db, step.id), rejected_urls)
    return to_resource_response(step.id, resolved, cached=False)


@router.post(
    "/{step_id}/resources/{resource_id}/not-useful",
    status_code=status.HTTP_204_NO_CONTENT,
)
def reject_step_resource(
    step_id: UUID,
    resource_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> Response:
    step, roadmap, _ = get_owned_active_step(db, user, step_id)
    owned_roadmap = get_owned_roadmap(db, user, roadmap.id)
    if calculate_roadmap_progress(db, user, owned_roadmap).current_step_id != step.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resources are available when this step becomes current",
        )
    resource = db.scalar(
        select(RoadmapStepResource).where(
            RoadmapStepResource.id == resource_id,
            RoadmapStepResource.step_id == step.id,
        )
    )
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource was not found")
    already_rejected = db.scalar(
        select(RoadmapStepResourceFeedback.id).where(
            RoadmapStepResourceFeedback.user_id == user.id,
            RoadmapStepResourceFeedback.step_id == step.id,
            RoadmapStepResourceFeedback.resource_url == resource.url,
        )
    )
    if already_rejected is None:
        db.add(
            RoadmapStepResourceFeedback(
                user_id=user.id,
                step_id=step.id,
                resource_url=resource.url,
            )
        )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{step_id}/resources/{resource_id}/not-useful",
    status_code=status.HTTP_204_NO_CONTENT,
)
def restore_step_resource(
    step_id: UUID,
    resource_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> Response:
    step, roadmap, _ = get_owned_active_step(db, user, step_id)
    owned_roadmap = get_owned_roadmap(db, user, roadmap.id)
    if calculate_roadmap_progress(db, user, owned_roadmap).current_step_id != step.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resources are available when this step becomes current",
        )
    resource = db.scalar(
        select(RoadmapStepResource).where(
            RoadmapStepResource.id == resource_id,
            RoadmapStepResource.step_id == step.id,
        )
    )
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource was not found")
    feedback = db.scalar(
        select(RoadmapStepResourceFeedback).where(
            RoadmapStepResourceFeedback.user_id == user.id,
            RoadmapStepResourceFeedback.step_id == step.id,
            RoadmapStepResourceFeedback.resource_url == resource.url,
        )
    )
    if feedback is not None:
        db.delete(feedback)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
