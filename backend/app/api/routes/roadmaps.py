from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_user
from app.api.schemas import RoadmapRead
from app.db.models import Goal, RoadmapMilestone, RoadmapVersion, User
from app.db.session import get_db

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])


def get_owned_roadmap(db: Session, user: User, roadmap_id: UUID) -> RoadmapVersion:
    roadmap = db.scalar(
        select(RoadmapVersion)
        .join(Goal, Goal.id == RoadmapVersion.goal_id)
        .where(RoadmapVersion.id == roadmap_id, Goal.user_id == user.id)
        .options(
            selectinload(RoadmapVersion.milestones).selectinload(RoadmapMilestone.steps)
        )
    )
    if roadmap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap not found")
    return roadmap


@router.get("/{roadmap_id}", response_model=RoadmapRead)
def read_roadmap(
    roadmap_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoadmapVersion:
    return get_owned_roadmap(db, user, roadmap_id)


@router.post("/{roadmap_id}/accept", response_model=RoadmapRead)
def accept_roadmap(
    roadmap_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoadmapVersion:
    roadmap = get_owned_roadmap(db, user, roadmap_id)
    if roadmap.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a draft roadmap can be accepted",
        )

    db.execute(
        update(RoadmapVersion)
        .where(
            RoadmapVersion.goal_id == roadmap.goal_id,
            RoadmapVersion.status == "accepted",
        )
        .values(status="superseded")
    )
    roadmap.status = "accepted"
    roadmap.accepted_at = datetime.now(UTC)
    goal = db.get(Goal, roadmap.goal_id)
    if goal is not None:
        goal.status = "active"
    db.commit()
    return get_owned_roadmap(db, user, roadmap.id)
