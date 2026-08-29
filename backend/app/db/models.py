from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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


class RoadmapVersion(Base):
    __tablename__ = "roadmap_versions"
    __table_args__ = (UniqueConstraint("goal_id", "version", name="uq_goal_roadmap_version"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    goal_id: Mapped[UUID] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    title: Mapped[str] = mapped_column(String(180))
    summary: Mapped[str] = mapped_column(Text)
    generation_source: Mapped[str] = mapped_column(String(40), default="fixture")
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
    kind: Mapped[str] = mapped_column(String(24))
    title: Mapped[str] = mapped_column(String(180))
    objective: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    completion_condition: Mapped[str] = mapped_column(Text)
    effort_label: Mapped[str] = mapped_column(String(40))

    milestone: Mapped[RoadmapMilestone] = relationship(back_populates="steps")
