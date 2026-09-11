from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import CurrentUser, DbSession
from app.api.schemas import RoadmapRead
from app.db.models import Goal, RoadmapMilestone, RoadmapPracticeCompletion, RoadmapVersion, User
from app.services.progress import to_roadmap_read

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
    user: CurrentUser,
    db: DbSession,
) -> RoadmapRead:
    return to_roadmap_read(db, user, get_owned_roadmap(db, user, roadmap_id))


@router.post("/{roadmap_id}/accept", response_model=RoadmapRead)
def accept_roadmap(
    roadmap_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> RoadmapRead:
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
    return to_roadmap_read(db, user, get_owned_roadmap(db, user, roadmap.id))


@router.put("/{roadmap_id}/practice/today", response_model=RoadmapRead)
def complete_today_practice(
    roadmap_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> RoadmapRead:
    roadmap = get_owned_roadmap(db, user, roadmap_id)
    if roadmap.status != "accepted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Accept this roadmap before logging practice",
        )
    task_count = len(roadmap.practice_tasks)
    if task_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This roadmap has no practice prompt yet",
        )
    now = datetime.now(UTC)
    practice_date = now.date()
    existing = db.scalar(
        select(RoadmapPracticeCompletion).where(
            RoadmapPracticeCompletion.user_id == user.id,
            RoadmapPracticeCompletion.roadmap_id == roadmap.id,
            RoadmapPracticeCompletion.practice_date == practice_date,
        )
    )
    if existing is None:
        db.add(
            RoadmapPracticeCompletion(
                user_id=user.id,
                roadmap_id=roadmap.id,
                practice_date=practice_date,
                task_index=int(now.timestamp() // 86_400) % task_count,
            )
        )
        db.commit()
    return to_roadmap_read(db, user, get_owned_roadmap(db, user, roadmap.id))
