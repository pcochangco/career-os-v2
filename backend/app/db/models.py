from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    goals: Mapped[list[Goal]] = relationship(back_populates="user", cascade="all, delete-orphan")
    step_progress: Mapped[list[RoadmapStepProgress]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    step_work: Mapped[list[RoadmapStepWork]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    generation_attempts: Mapped[list[RoadmapGenerationAttempt]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    user: Mapped[User] = relationship(back_populates="sessions")


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(140))
    status: Mapped[str] = mapped_column(String(32), default="discovery", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="goals")
    discovery_answers: Mapped[list[GoalDiscoveryAnswer]] = relationship(
        back_populates="goal", cascade="all, delete-orphan"
    )
    roadmaps: Mapped[list[RoadmapVersion]] = relationship(
        back_populates="goal", cascade="all, delete-orphan"
    )


class GoalDiscoveryAnswer(Base):
    __tablename__ = "goal_discovery_answers"
    __table_args__ = (
        UniqueConstraint("goal_id", "revision", "question_key", name="uq_goal_answer_revision_key"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    goal_id: Mapped[UUID] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    question_key: Mapped[str] = mapped_column(String(64))
    answer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    goal: Mapped[Goal] = relationship(back_populates="discovery_answers")


class RoadmapGenerationAttempt(Base):
    __tablename__ = "roadmap_generation_attempts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    requested_provider: Mapped[str] = mapped_column(String(24))
    outcome: Mapped[str] = mapped_column(String(24), default="started", index=True)
    resulting_source: Mapped[str] = mapped_column(String(40), default="")
    provider_model: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="generation_attempts")


class RoadmapVersion(Base):
    __tablename__ = "roadmap_versions"
    __table_args__ = (UniqueConstraint("goal_id", "version", name="uq_goal_roadmap_version"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    goal_id: Mapped[UUID] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    title: Mapped[str] = mapped_column(String(180))
    summary: Mapped[str] = mapped_column(Text)
    goal_outcome: Mapped[str] = mapped_column(Text, default="")
    starting_state_summary: Mapped[str] = mapped_column(Text, default="")
    assumptions: Mapped[list[str]] = mapped_column(JSON, default=list)
    schema_version: Mapped[str] = mapped_column(String(20), default="1.0")
    generation_source: Mapped[str] = mapped_column(String(40), default="fixture")
    provider_model: Mapped[str] = mapped_column(String(120), default="deterministic-fixture")
    prompt_version: Mapped[str] = mapped_column(String(120), default="")
    provider_response_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    input_snapshot: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    quality_report: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    quality_score: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    generation_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    goal: Mapped[Goal] = relationship(back_populates="roadmaps")
    milestones: Mapped[list[RoadmapMilestone]] = relationship(
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="RoadmapMilestone.position",
    )


class RoadmapMilestone(Base):
    __tablename__ = "roadmap_milestones"
    __table_args__ = (UniqueConstraint("roadmap_id", "position", name="uq_milestone_position"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    roadmap_id: Mapped[UUID] = mapped_column(
        ForeignKey("roadmap_versions.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(180))
    outcome: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text, default="")

    roadmap: Mapped[RoadmapVersion] = relationship(back_populates="milestones")
    steps: Mapped[list[RoadmapStep]] = relationship(
        back_populates="milestone",
        cascade="all, delete-orphan",
        order_by="RoadmapStep.position",
    )


class RoadmapStep(Base):
    __tablename__ = "roadmap_steps"
    __table_args__ = (UniqueConstraint("milestone_id", "position", name="uq_step_position"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    milestone_id: Mapped[UUID] = mapped_column(
        ForeignKey("roadmap_milestones.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    stable_key: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(24))
    title: Mapped[str] = mapped_column(String(180))
    objective: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text, default="")
    action: Mapped[str] = mapped_column(Text)
    completion_condition: Mapped[str] = mapped_column(Text)
    effort_label: Mapped[str] = mapped_column(String(80))
    evidence_suggestion: Mapped[str] = mapped_column(Text, default="")
    prerequisite_step_keys: Mapped[list[str]] = mapped_column(JSON, default=list)
    resource_queries: Mapped[list[str]] = mapped_column(JSON, default=list)

    milestone: Mapped[RoadmapMilestone] = relationship(back_populates="steps")
    progress_records: Mapped[list[RoadmapStepProgress]] = relationship(
        back_populates="step", cascade="all, delete-orphan"
    )
    work_records: Mapped[list[RoadmapStepWork]] = relationship(
        back_populates="step", cascade="all, delete-orphan"
    )
    resources: Mapped[list[RoadmapStepResource]] = relationship(
        back_populates="step", cascade="all, delete-orphan"
    )


class RoadmapStepDependency(Base):
    __tablename__ = "roadmap_step_dependencies"
    __table_args__ = (
        UniqueConstraint("step_id", "prerequisite_step_id", name="uq_step_prerequisite"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    step_id: Mapped[UUID] = mapped_column(
        ForeignKey("roadmap_steps.id", ondelete="CASCADE"), index=True
    )
    prerequisite_step_id: Mapped[UUID] = mapped_column(
        ForeignKey("roadmap_steps.id", ondelete="CASCADE"), index=True
    )


class RoadmapStepProgress(Base):
    __tablename__ = "roadmap_step_progress"
    __table_args__ = (UniqueConstraint("user_id", "step_id", name="uq_user_step_progress"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    step_id: Mapped[UUID] = mapped_column(
        ForeignKey("roadmap_steps.id", ondelete="CASCADE"), index=True
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped[User] = relationship(back_populates="step_progress")
    step: Mapped[RoadmapStep] = relationship(back_populates="progress_records")


class RoadmapStepWork(Base):
    __tablename__ = "roadmap_step_work"
    __table_args__ = (UniqueConstraint("user_id", "step_id", name="uq_user_step_work"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    step_id: Mapped[UUID] = mapped_column(
        ForeignKey("roadmap_steps.id", ondelete="CASCADE"), index=True
    )
    notes: Mapped[str] = mapped_column(Text, default="")
    evidence_summary: Mapped[str] = mapped_column(Text, default="")
    evidence_url: Mapped[str] = mapped_column(String(2048), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="step_work")
    step: Mapped[RoadmapStep] = relationship(back_populates="work_records")


class RoadmapStepResource(Base):
    __tablename__ = "roadmap_step_resources"
    __table_args__ = (UniqueConstraint("step_id", "url", name="uq_step_resource_url"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    step_id: Mapped[UUID] = mapped_column(
        ForeignKey("roadmap_steps.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(40))
    resource_type: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(String(2048))
    source_name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    why_relevant: Mapped[str] = mapped_column(Text, default="")
    thumbnail_url: Mapped[str] = mapped_column(String(2048), default="")
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    step: Mapped[RoadmapStep] = relationship(back_populates="resources")
