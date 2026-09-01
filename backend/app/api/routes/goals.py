from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.ai.dependencies import DiscoveryService, GenerationService, fixture_service
from app.ai.schema import DiscoveryContextAnswer, RoadmapGenerationInput
from app.api.dependencies import CurrentUser, DbSession
from app.api.schemas import (
    DiscoveryAnswerWrite,
    DiscoveryOptionRead,
    DiscoveryQuestionRead,
    DiscoveryStateRead,
    DiscoveryWrite,
    GoalCreate,
    GoalRead,
    RoadmapRead,
)
from app.core.config import get_settings
from app.db.models import (
    Goal,
    GoalDiscoveryAnswer,
    GoalDiscoveryQuestion,
    RoadmapGenerationAttempt,
    RoadmapMilestone,
    RoadmapStep,
    RoadmapStepDependency,
    RoadmapVersion,
    User,
)
from app.discovery.service import MAX_DISCOVERY_QUESTIONS, MIN_DISCOVERY_QUESTIONS
from app.services.progress import calculate_roadmap_progress

router = APIRouter(prefix="/goals", tags=["goals"])


def get_owned_goal(db: Session, user: User, goal_id: UUID) -> Goal:
    goal = db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user.id))
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return goal


def to_goal_read(db: Session, goal: Goal) -> GoalRead:
    active_roadmap = db.scalar(
        select(RoadmapVersion)
        .where(RoadmapVersion.goal_id == goal.id, RoadmapVersion.status == "accepted")
        .order_by(RoadmapVersion.version.desc())
        .limit(1)
        .options(selectinload(RoadmapVersion.milestones).selectinload(RoadmapMilestone.steps))
    )
    draft_id = db.scalar(
        select(RoadmapVersion.id)
        .where(RoadmapVersion.goal_id == goal.id, RoadmapVersion.status == "draft")
        .order_by(RoadmapVersion.version.desc())
        .limit(1)
    )
    progress = calculate_roadmap_progress(db, goal.user, active_roadmap) if active_roadmap else None
    return GoalRead(
        id=goal.id,
        title=goal.title,
        status=goal.status,
        created_at=goal.created_at,
        active_roadmap_id=active_roadmap.id if active_roadmap else None,
        latest_draft_roadmap_id=draft_id,
        completed_steps=progress.completed_steps if progress else 0,
        total_steps=progress.total_steps if progress else 0,
        progress_percent=progress.progress_percent if progress else 0,
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


def latest_question_revision(db: Session, goal: Goal) -> int | None:
    return db.scalar(
        select(func.max(GoalDiscoveryQuestion.revision)).where(
            GoalDiscoveryQuestion.goal_id == goal.id
        )
    )


def adaptive_questions(db: Session, goal: Goal, revision: int) -> list[GoalDiscoveryQuestion]:
    return db.scalars(
        select(GoalDiscoveryQuestion)
        .where(
            GoalDiscoveryQuestion.goal_id == goal.id,
            GoalDiscoveryQuestion.revision == revision,
        )
        .order_by(GoalDiscoveryQuestion.position)
    ).all()


def adaptive_context(
    db: Session,
    goal: Goal,
    revision: int,
) -> list[DiscoveryContextAnswer]:
    questions = adaptive_questions(db, goal, revision)
    answers = {
        answer.question_key: answer.answer
        for answer in db.scalars(
            select(GoalDiscoveryAnswer).where(
                GoalDiscoveryAnswer.goal_id == goal.id,
                GoalDiscoveryAnswer.revision == revision,
            )
        ).all()
    }
    return [
        DiscoveryContextAnswer(
            question_key=question.question_key,
            question=question.question,
            answer=answers[question.question_key],
            skipped=question.status == "skipped",
        )
        for question in questions
        if question.status in {"answered", "skipped"} and question.question_key in answers
    ]


def to_discovery_question_read(question: GoalDiscoveryQuestion) -> DiscoveryQuestionRead:
    return DiscoveryQuestionRead(
        id=question.id,
        position=question.position,
        question_key=question.question_key,
        question=question.question,
        help_text=question.help_text,
        selection_mode="multiple",
        options=[DiscoveryOptionRead.model_validate(option) for option in question.options],
        placeholder=question.placeholder,
    )


def to_discovery_state(db: Session, goal: Goal) -> DiscoveryStateRead:
    revision = latest_question_revision(db, goal)
    if revision is None:
        return DiscoveryStateRead(
            status="unstarted",
            goal_title=goal.title,
            minimum_questions=MIN_DISCOVERY_QUESTIONS,
            maximum_questions=MAX_DISCOVERY_QUESTIONS,
        )
    questions = adaptive_questions(db, goal, revision)
    answered_questions = sum(question.status in {"answered", "skipped"} for question in questions)
    pending = next(
        (question for question in reversed(questions) if question.status == "pending"), None
    )
    if pending is not None:
        return DiscoveryStateRead(
            status="question",
            goal_title=goal.title,
            question=to_discovery_question_read(pending),
            answered_questions=answered_questions,
            minimum_questions=MIN_DISCOVERY_QUESTIONS,
            maximum_questions=MAX_DISCOVERY_QUESTIONS,
        )
    context = adaptive_context(db, goal, revision)
    if goal.status == "ready_to_generate":
        return DiscoveryStateRead(
            status="ready",
            goal_title=goal.title,
            context_summary=[f"{answer.question}: {answer.answer}" for answer in context],
            completion_reason="You have given enough detail to shape a focused roadmap.",
            answered_questions=answered_questions,
            minimum_questions=MIN_DISCOVERY_QUESTIONS,
            maximum_questions=MAX_DISCOVERY_QUESTIONS,
        )
    return DiscoveryStateRead(
        status="unstarted",
        goal_title=goal.title,
        answered_questions=answered_questions,
        minimum_questions=MIN_DISCOVERY_QUESTIONS,
        maximum_questions=MAX_DISCOVERY_QUESTIONS,
    )


def apply_goal_title_suggestion(goal: Goal, suggested_title: str) -> None:
    """Apply the first-turn presentation correction without changing the goal's meaning."""
    normalized = " ".join(suggested_title.split()).strip(" .")
    if 3 <= len(normalized) <= 140:
        goal.title = normalized


def start_next_discovery_question(
    *,
    db: Session,
    goal: Goal,
    discovery_service: DiscoveryService,
) -> DiscoveryStateRead:
    state = to_discovery_state(db, goal)
    if state.status != "unstarted":
        return state

    existing_revision = latest_question_revision(db, goal)
    if existing_revision is not None and adaptive_questions(db, goal, existing_revision):
        return advance_discovery(
            db=db,
            goal=goal,
            discovery_service=discovery_service,
            revision=existing_revision,
        )

    latest_answer_revision = db.scalar(
        select(func.max(GoalDiscoveryAnswer.revision)).where(GoalDiscoveryAnswer.goal_id == goal.id)
    )
    revision = (latest_answer_revision or 0) + 1
    context: list[DiscoveryContextAnswer] = []
    result = discovery_service.next_question(
        goal_title=goal.title,
        answers=context,
        used_question_keys=[],
    )
    if result.value.is_complete:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "CareerOS needs a little more context before it can shape your roadmap. "
                "Please try again."
            ),
        )
    question = result.value
    apply_goal_title_suggestion(goal, question.suggested_goal_title)
    goal.status = "discovery"
    db.add(
        GoalDiscoveryQuestion(
            goal_id=goal.id,
            revision=revision,
            position=1,
            question_key=question.question_key,
            question=question.question,
            help_text=question.help_text,
            selection_mode="multiple",
            options=[option.model_dump() for option in question.options],
            placeholder=question.placeholder,
        )
    )
    db.commit()
    db.refresh(goal)
    return to_discovery_state(db, goal)


def advance_discovery(
    *,
    db: Session,
    goal: Goal,
    discovery_service: DiscoveryService,
    revision: int,
) -> DiscoveryStateRead:
    context = adaptive_context(db, goal, revision)
    questions = adaptive_questions(db, goal, revision)
    result = discovery_service.next_question(
        goal_title=goal.title,
        answers=context,
        used_question_keys=[question.question_key for question in questions],
    )
    if result.value.is_complete:
        goal.status = "ready_to_generate"
        db.commit()
        db.refresh(goal)
        return to_discovery_state(db, goal)

    question = result.value
    db.add(
        GoalDiscoveryQuestion(
            goal_id=goal.id,
            revision=revision,
            position=len(questions) + 1,
            question_key=question.question_key,
            question=question.question,
            help_text=question.help_text,
            selection_mode="multiple",
            options=[option.model_dump() for option in question.options],
            placeholder=question.placeholder,
        )
    )
    db.commit()
    db.refresh(goal)
    return to_discovery_state(db, goal)


@router.get("/{goal_id}/discovery", response_model=DiscoveryStateRead)
def read_adaptive_discovery(
    goal_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> DiscoveryStateRead:
    return to_discovery_state(db, get_owned_goal(db, user, goal_id))


@router.post("/{goal_id}/discovery/questions/next", response_model=DiscoveryStateRead)
def begin_adaptive_discovery(
    goal_id: UUID,
    user: CurrentUser,
    db: DbSession,
    discovery_service: DiscoveryService,
) -> DiscoveryStateRead:
    goal = get_owned_goal(db, user, goal_id)
    if goal.status in {"active", "completed"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This goal already has a roadmap"
        )
    return start_next_discovery_question(db=db, goal=goal, discovery_service=discovery_service)


@router.post(
    "/{goal_id}/discovery/questions/{question_id}/answer", response_model=DiscoveryStateRead
)
def answer_adaptive_discovery_question(
    goal_id: UUID,
    question_id: UUID,
    payload: DiscoveryAnswerWrite,
    user: CurrentUser,
    db: DbSession,
    discovery_service: DiscoveryService,
) -> DiscoveryStateRead:
    goal = get_owned_goal(db, user, goal_id)
    question = db.scalar(
        select(GoalDiscoveryQuestion).where(
            GoalDiscoveryQuestion.id == question_id,
            GoalDiscoveryQuestion.goal_id == goal.id,
        )
    )
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Discovery question not found"
        )
    if question.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This question was already answered"
        )

    options_by_key = {option["key"]: option["label"] for option in question.options}
    unknown_keys = set(payload.selected_option_keys) - set(options_by_key)
    if unknown_keys:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Choose one of the listed answers",
        )
    selected_labels = [options_by_key[key] for key in payload.selected_option_keys]
    answer_parts = selected_labels + ([payload.custom_answer] if payload.custom_answer else [])
    answer_text = "Skipped" if payload.skipped else "; ".join(answer_parts)
    question.status = "skipped" if payload.skipped else "answered"
    question.answered_at = datetime.now(UTC)
    db.add(
        GoalDiscoveryAnswer(
            goal_id=goal.id,
            revision=question.revision,
            question_key=question.question_key,
            answer=answer_text,
        )
    )
    db.commit()
    db.refresh(goal)
    return advance_discovery(
        db=db,
        goal=goal,
        discovery_service=discovery_service,
        revision=question.revision,
    )


def latest_discovery(db: Session, goal: Goal) -> RoadmapGenerationInput:
    adaptive_revision = latest_question_revision(db, goal)
    if adaptive_revision is not None:
        context = adaptive_context(db, goal, adaptive_revision)
        if not context or goal.status != "ready_to_generate":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Complete discovery before generating a roadmap",
            )
        return RoadmapGenerationInput(
            goal_title=goal.title,
            desired_outcome=f"Achieve the goal: {goal.title}",
            current_level=(
                "Use the learner's discovery answers to establish their starting point."
            ),
            existing_experience=(
                "Use the learner's discovery answers to identify existing experience."
            ),
            relevant_constraints=(
                "Use the learner's discovery answers to identify preferences and constraints."
            ),
            proof_of_completion=(
                "Use the learner's discovery answers to define convincing proof of completion."
            ),
            discovery_context=context,
        )
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
    return RoadmapGenerationInput(
        goal_title=goal.title,
        **DiscoveryWrite(**{answer.question_key: answer.answer for answer in answers}).model_dump(),
    )


def start_generation_attempt(
    db: Session, user: User
) -> tuple[RoadmapGenerationAttempt, bool]:
    settings = get_settings()
    live_generation_requested = settings.ai_mode == "live" or (
        settings.ai_mode == "auto" and settings.ai_configured
    )
    window_start = datetime.now(UTC) - timedelta(hours=1)
    user_attempts = db.scalar(
        select(func.count(RoadmapGenerationAttempt.id)).where(
            RoadmapGenerationAttempt.user_id == user.id,
            RoadmapGenerationAttempt.created_at >= window_start,
            RoadmapGenerationAttempt.requested_provider != "fixture",
        )
    )
    global_attempts = db.scalar(
        select(func.count(RoadmapGenerationAttempt.id)).where(
            RoadmapGenerationAttempt.created_at >= window_start,
            RoadmapGenerationAttempt.requested_provider != "fixture",
        )
    )
    use_quota_fallback = live_generation_requested and (
        (user_attempts or 0) >= settings.ai_generation_limit_per_hour
        or (global_attempts or 0) >= settings.ai_global_generation_limit_per_hour
    )

    attempt = RoadmapGenerationAttempt(
        user_id=user.id,
        requested_provider=(
            "fixture"
            if settings.ai_mode == "fixture" or use_quota_fallback
            else settings.ai_provider
        ),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt, use_quota_fallback


def finish_generation_attempt(
    db: Session,
    attempt: RoadmapGenerationAttempt,
    *,
    outcome: str,
    resulting_source: str = "",
    provider_model: str = "",
) -> None:
    attempt.outcome = outcome
    attempt.resulting_source = resulting_source
    attempt.provider_model = provider_model
    attempt.completed_at = datetime.now(UTC)
    db.commit()


@router.post("/{goal_id}/roadmaps", response_model=RoadmapRead, status_code=status.HTTP_201_CREATED)
def generate_roadmap(
    goal_id: UUID,
    user: CurrentUser,
    db: DbSession,
    generation_service: GenerationService,
) -> RoadmapVersion:
    goal = get_owned_goal(db, user, goal_id)
    generation_input = latest_discovery(db, goal)
    attempt, use_quota_fallback = start_generation_attempt(db, user)
    settings = get_settings()
    effective_generation_service = (
        fixture_service(settings) if use_quota_fallback else generation_service
    )
    try:
        generated = effective_generation_service.generate(generation_input)
    except Exception:
        finish_generation_attempt(db, attempt, outcome="failed")
        raise
    used_live_fallback = (
        settings.ai_mode in {"auto", "live"}
        and settings.ai_configured
        and generated.provider == "fixture"
    )
    attempt_outcome = (
        "quota_fallback"
        if use_quota_fallback
        else "fallback"
        if used_live_fallback
        else "succeeded"
        if generated.provider != "fixture"
        else "preview"
    )
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
    finish_generation_attempt(
        db,
        attempt,
        outcome=attempt_outcome,
        resulting_source=generated.provider,
        provider_model=generated.model,
    )
    return db.get(RoadmapVersion, roadmap.id)
