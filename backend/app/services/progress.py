from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import RoadmapMilestoneRead, RoadmapRead, RoadmapStepRead
from app.db.models import (
    RoadmapStep,
    RoadmapStepProgress,
    RoadmapStepWork,
    RoadmapVersion,
    User,
)


@dataclass(frozen=True)
class RoadmapProgressSnapshot:
    statuses: dict[UUID, str]
    completed_at: dict[UUID, datetime]
    completed_steps: int
    total_steps: int
    progress_percent: int
    current_step_id: UUID | None


def flattened_steps(roadmap: RoadmapVersion) -> list[RoadmapStep]:
    return [step for milestone in roadmap.milestones for step in milestone.steps]


def calculate_roadmap_progress(
    db: Session,
    user: User,
    roadmap: RoadmapVersion,
) -> RoadmapProgressSnapshot:
    steps = flattened_steps(roadmap)
    step_ids = [step.id for step in steps]
    progress_rows = (
        db.scalars(
            select(RoadmapStepProgress).where(
                RoadmapStepProgress.user_id == user.id,
                RoadmapStepProgress.step_id.in_(step_ids),
            )
        ).all()
        if step_ids
        else []
    )
    completed_at = {row.step_id: row.completed_at for row in progress_rows}
    completed_keys = {step.stable_key for step in steps if step.id in completed_at}

    statuses: dict[UUID, str] = {}
    for step in steps:
        if step.id in completed_at:
            statuses[step.id] = "completed"
        elif set(step.prerequisite_step_keys).issubset(completed_keys):
            statuses[step.id] = "upcoming"
        else:
            statuses[step.id] = "blocked"

    current_step_id = (
        next(
            (step.id for step in steps if statuses[step.id] == "upcoming"),
            None,
        )
        if roadmap.status == "accepted"
        else None
    )
    if current_step_id is not None:
        statuses[current_step_id] = "current"

    total_steps = len(steps)
    completed_steps = len(completed_at)
    progress_percent = (completed_steps * 100 // total_steps) if total_steps else 0
    return RoadmapProgressSnapshot(
        statuses=statuses,
        completed_at=completed_at,
        completed_steps=completed_steps,
        total_steps=total_steps,
        progress_percent=progress_percent,
        current_step_id=current_step_id,
    )


def to_roadmap_read(db: Session, user: User, roadmap: RoadmapVersion) -> RoadmapRead:
    snapshot = calculate_roadmap_progress(db, user, roadmap)
    step_ids = [step.id for step in flattened_steps(roadmap)]
    work_by_step = (
        {
            work.step_id: work
            for work in db.scalars(
                select(RoadmapStepWork).where(
                    RoadmapStepWork.user_id == user.id,
                    RoadmapStepWork.step_id.in_(step_ids),
                )
            ).all()
        }
        if step_ids
        else {}
    )
    milestones: list[RoadmapMilestoneRead] = []
    for milestone in roadmap.milestones:
        steps: list[RoadmapStepRead] = []
        for step in milestone.steps:
            work = work_by_step.get(step.id)
            steps.append(
                RoadmapStepRead.model_validate(step).model_copy(
                    update={
                        "progress_status": snapshot.statuses[step.id],
                        "completed_at": snapshot.completed_at.get(step.id),
                        "notes": work.notes if work else "",
                        "evidence_summary": work.evidence_summary if work else "",
                        "evidence_url": work.evidence_url if work else "",
                        "work_updated_at": work.updated_at if work else None,
                    }
                )
            )
        milestones.append(
            RoadmapMilestoneRead.model_validate(milestone).model_copy(update={"steps": steps})
        )

    return RoadmapRead.model_validate(roadmap).model_copy(
        update={
            "completed_steps": snapshot.completed_steps,
            "total_steps": snapshot.total_steps,
            "progress_percent": snapshot.progress_percent,
            "current_step_id": snapshot.current_step_id,
            "milestones": milestones,
        }
    )
