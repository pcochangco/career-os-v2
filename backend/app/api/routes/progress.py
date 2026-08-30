from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, DbSession
from app.api.routes.roadmaps import get_owned_roadmap
from app.api.schemas import RoadmapRead, StepProgressWrite
from app.db.models import (
    Goal,
    RoadmapMilestone,
    RoadmapStep,
    RoadmapStepDependency,
    RoadmapStepProgress,
    RoadmapVersion,
    User,
)
from app.services.progress import calculate_roadmap_progress, to_roadmap_read

router = APIRouter(prefix="/roadmap-steps", tags=["progress"])


def get_owned_active_step(
    db: Session,
    user: User,
    step_id: UUID,
) -> tuple[RoadmapStep, RoadmapVersion, Goal]:
    result = db.execute(
        select(RoadmapStep, RoadmapVersion, Goal)
        .join(RoadmapMilestone, RoadmapMilestone.id == RoadmapStep.milestone_id)
        .join(RoadmapVersion, RoadmapVersion.id == RoadmapMilestone.roadmap_id)
        .join(Goal, Goal.id == RoadmapVersion.goal_id)
        .where(
            RoadmapStep.id == step_id,
            RoadmapVersion.status == "accepted",
            Goal.user_id == user.id,
        )
    ).one_or_none()
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active roadmap step not found",
        )
    return result


def ensure_prerequisites_completed(db: Session, user: User, step: RoadmapStep) -> None:
    prerequisite_ids = set(
        db.scalars(
            select(RoadmapStepDependency.prerequisite_step_id).where(
                RoadmapStepDependency.step_id == step.id
            )
        ).all()
    )
    if not prerequisite_ids:
        return
    completed_ids = set(
        db.scalars(
            select(RoadmapStepProgress.step_id).where(
                RoadmapStepProgress.user_id == user.id,
                RoadmapStepProgress.step_id.in_(prerequisite_ids),
            )
        ).all()
    )
    if completed_ids != prerequisite_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Complete this step's prerequisites first",
        )


def ensure_no_completed_dependents(db: Session, user: User, step: RoadmapStep) -> None:
    completed_dependent = db.scalar(
        select(RoadmapStepProgress.id)
        .join(
            RoadmapStepDependency,
            RoadmapStepDependency.step_id == RoadmapStepProgress.step_id,
        )
        .where(
            RoadmapStepProgress.user_id == user.id,
            RoadmapStepDependency.prerequisite_step_id == step.id,
        )
        .limit(1)
    )
    if completed_dependent is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reopen dependent steps before reopening this step",
        )


def update_goal_status(db: Session, user: User, roadmap: RoadmapVersion, goal: Goal) -> None:
    total_steps = db.scalar(
        select(func.count(RoadmapStep.id))
        .join(RoadmapMilestone, RoadmapMilestone.id == RoadmapStep.milestone_id)
        .where(RoadmapMilestone.roadmap_id == roadmap.id)
    )
    completed_steps = db.scalar(
        select(func.count(RoadmapStepProgress.id))
        .join(RoadmapStep, RoadmapStep.id == RoadmapStepProgress.step_id)
        .join(RoadmapMilestone, RoadmapMilestone.id == RoadmapStep.milestone_id)
        .where(
            RoadmapStepProgress.user_id == user.id,
            RoadmapMilestone.roadmap_id == roadmap.id,
        )
    )
    goal.status = (
        "completed"
        if total_steps and completed_steps == total_steps
        else "active"
    )


@router.put("/{step_id}/progress", response_model=RoadmapRead)
def write_step_progress(
    step_id: UUID,
    payload: StepProgressWrite,
    user: CurrentUser,
    db: DbSession,
) -> RoadmapRead:
    step, roadmap, goal = get_owned_active_step(db, user, step_id)
    owned_roadmap = get_owned_roadmap(db, user, roadmap.id)
    progress = db.scalar(
        select(RoadmapStepProgress).where(
            RoadmapStepProgress.user_id == user.id,
            RoadmapStepProgress.step_id == step.id,
        )
    )

    if payload.completed and progress is None:
        current_step_id = calculate_roadmap_progress(db, user, owned_roadmap).current_step_id
        if current_step_id != step.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Complete the current roadmap step first",
            )
        ensure_prerequisites_completed(db, user, step)
        db.add(
            RoadmapStepProgress(
                user_id=user.id,
                step_id=step.id,
                completed_at=datetime.now(UTC),
            )
        )
    elif not payload.completed and progress is not None:
        ensure_no_completed_dependents(db, user, step)
        db.delete(progress)

    db.flush()
    update_goal_status(db, user, roadmap, goal)
    db.commit()
    return to_roadmap_read(db, user, get_owned_roadmap(db, user, roadmap.id))
