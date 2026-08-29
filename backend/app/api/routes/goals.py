from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.dependencies import GenerationService
from app.ai.schema import RoadmapGenerationInput
from app.api.dependencies import CurrentUser, DbSession
from app.api.schemas import DiscoveryWrite, GoalCreate, GoalRead, RoadmapRead
from app.db.models import (
    Goal,
    GoalDiscoveryAnswer,
    RoadmapMilestone,
    RoadmapStep,
    RoadmapStepDependency,
    RoadmapVersion,
    User,
)

router = APIRouter(prefix="/goals", tags=["goals"])


def get_owned_goal(db: Session, user: User, goal_id: UUID) -> Goal:
    goal = db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user.id))
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return goal


def to_goal_read(db: Session, goal: Goal) -> GoalRead:
    active_id = db.scalar(
        select(RoadmapVersion.id)
        .where(RoadmapVersion.goal_id == goal.id, RoadmapVersion.status == "accepted")
        .order_by(RoadmapVersion.version.desc())
        .limit(1)
    )
    draft_id = db.scalar(
        select(RoadmapVersion.id)
        .where(RoadmapVersion.goal_id == goal.id, RoadmapVersion.status == "draft")
        .order_by(RoadmapVersion.version.desc())
        .limit(1)
    )
    return GoalRead(
        id=goal.id,
        title=goal.title,
        status=goal.status,
        created_at=goal.created_at,
        active_roadmap_id=active_id,
        latest_draft_roadmap_id=draft_id,
    )


@router.get("", response_model=list[GoalRead])
def list_goals(
    user: CurrentUser,
    db: DbSession,
) -> list[GoalRead]:
    goals = db.scalars(
        select(Goal).where(Goal.user_id == user.id).order_by(Goal.updated_at.desc())
    ).all()
    return [to_goal_read(db, goal) for goal in goals]


@router.post("", response_model=GoalRead, status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: GoalCreate,
    user: CurrentUser,
    db: DbSession,
) -> GoalRead:
    goal = Goal(user_id=user.id, title=payload.title.strip())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return to_goal_read(db, goal)


@router.get("/{goal_id}", response_model=GoalRead)
def read_goal(
    goal_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> GoalRead:
    return to_goal_read(db, get_owned_goal(db, user, goal_id))


@router.put("/{goal_id}/discovery", response_model=GoalRead)
def save_discovery(
    goal_id: UUID,
    payload: DiscoveryWrite,
    user: CurrentUser,
    db: DbSession,
) -> GoalRead:
    goal = get_owned_goal(db, user, goal_id)
    latest_revision = db.scalar(
        select(func.max(GoalDiscoveryAnswer.revision)).where(GoalDiscoveryAnswer.goal_id == goal.id)
    )
    revision = (latest_revision or 0) + 1
    for question_key, answer in payload.model_dump().items():
        db.add(
            GoalDiscoveryAnswer(
                goal_id=goal.id,
                revision=revision,
                question_key=question_key,
                answer=answer.strip(),
            )
        )
    goal.status = "ready_to_generate"
    db.commit()
    db.refresh(goal)
    return to_goal_read(db, goal)


def latest_discovery(db: Session, goal: Goal) -> DiscoveryWrite:
    latest_revision = db.scalar(
        select(func.max(GoalDiscoveryAnswer.revision)).where(GoalDiscoveryAnswer.goal_id == goal.id)
    )
    if latest_revision is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Complete discovery before generating a roadmap",
        )
    answers = db.scalars(
        select(GoalDiscoveryAnswer).where(
            GoalDiscoveryAnswer.goal_id == goal.id,
            GoalDiscoveryAnswer.revision == latest_revision,
        )
    ).all()
    return DiscoveryWrite(**{answer.question_key: answer.answer for answer in answers})


@router.post("/{goal_id}/roadmaps", response_model=RoadmapRead, status_code=status.HTTP_201_CREATED)
def generate_roadmap(
    goal_id: UUID,
    user: CurrentUser,
    db: DbSession,
    generation_service: GenerationService,
) -> RoadmapVersion:
    goal = get_owned_goal(db, user, goal_id)
    discovery = latest_discovery(db, goal)
    generation_input = RoadmapGenerationInput(
        goal_title=goal.title,
        **discovery.model_dump(),
    )
    generated = generation_service.generate(generation_input)
    draft = generated.draft
    latest_version = db.scalar(
        select(func.max(RoadmapVersion.version)).where(RoadmapVersion.goal_id == goal.id)
    )
    roadmap = RoadmapVersion(
        goal_id=goal.id,
        version=(latest_version or 0) + 1,
        title=draft.title,
        summary=draft.summary,
        goal_outcome=draft.goal_outcome,
        starting_state_summary=draft.starting_state_summary,
        assumptions=draft.assumptions,
        schema_version=draft.schema_version,
        status="draft",
        generation_source=generated.provider,
        provider_model=generated.model,
        prompt_version=generated.prompt_version,
        provider_response_ids=list(generated.response_ids),
        input_snapshot=generation_input.model_dump(),
        quality_report=generated.quality.model_dump(),
        quality_score=generated.quality.final_score,
        input_tokens=generated.input_tokens,
        output_tokens=generated.output_tokens,
        generation_duration_ms=generated.duration_ms,
    )
    db.add(roadmap)
    db.flush()
    step_by_key: dict[str, RoadmapStep] = {}
    pending_dependencies: list[tuple[RoadmapStep, list[str]]] = []
    for milestone_position, draft_milestone in enumerate(draft.milestones, start=1):
        milestone = RoadmapMilestone(
            roadmap_id=roadmap.id,
            position=milestone_position,
            title=draft_milestone.title,
            outcome=draft_milestone.outcome,
            rationale=draft_milestone.rationale,
        )
        db.add(milestone)
        db.flush()
        for step_position, draft_step in enumerate(draft_milestone.steps, start=1):
            step = RoadmapStep(
                milestone_id=milestone.id,
                position=step_position,
                stable_key=draft_step.stable_key,
                kind=draft_step.kind,
                title=draft_step.title,
                objective=draft_step.objective,
                rationale=draft_step.rationale,
                action=draft_step.action,
                completion_condition=draft_step.completion_condition,
                effort_label=draft_step.effort_label,
                evidence_suggestion=draft_step.evidence_suggestion,
                prerequisite_step_keys=draft_step.prerequisite_step_keys,
                resource_queries=draft_step.resource_queries,
            )
            db.add(step)
            db.flush()
            step_by_key[draft_step.stable_key] = step
            pending_dependencies.append((step, draft_step.prerequisite_step_keys))

    for step, prerequisite_keys in pending_dependencies:
        for prerequisite_key in prerequisite_keys:
            prerequisite = step_by_key[prerequisite_key]
            db.add(
                RoadmapStepDependency(
                    step_id=step.id,
                    prerequisite_step_id=prerequisite.id,
                )
            )
    goal.status = "roadmap_review"
    db.commit()
    return db.get(RoadmapVersion, roadmap.id)
