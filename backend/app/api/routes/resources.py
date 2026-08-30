from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentUser, DbSession
from app.api.routes.progress import get_owned_active_step
from app.api.routes.roadmaps import get_owned_roadmap
from app.api.schemas import LearningResourceRead, StepResourcesRead
from app.db.models import RoadmapStepResource
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


@router.post("/{step_id}/resources/resolve", response_model=StepResourcesRead)
def resolve_step_resources(
    step_id: UUID,
    user: CurrentUser,
    db: DbSession,
    resolver: Resolver,
) -> StepResourcesRead:
    step, roadmap, _ = get_owned_active_step(db, user, step_id)
    owned_roadmap = get_owned_roadmap(db, user, roadmap.id)
    if calculate_roadmap_progress(db, user, owned_roadmap).current_step_id != step.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resources are available when this step becomes current",
        )

    cached = read_cached_resources(db, step.id)
    if cached:
        return to_resource_response(step.id, cached, cached=True)

    candidates = resolver.resolve(step.resource_queries)
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
    ]
    db.add_all(resources)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return to_resource_response(step.id, read_cached_resources(db, step.id), cached=False)
