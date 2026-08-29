"""Add Sprint 1 goal and roadmap tables.

Revision ID: 20260829_0001
Revises:
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260829_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True)
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])
    op.create_table(
        "goals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_goals_user_id", "goals", ["user_id"])
    op.create_index("ix_goals_status", "goals", ["status"])
    op.create_table(
        "goal_discovery_answers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("question_key", sa.String(length=64), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "goal_id", "revision", "question_key", name="uq_goal_answer_revision_key"
        ),
    )
    op.create_index(
        "ix_goal_discovery_answers_goal_id", "goal_discovery_answers", ["goal_id"]
    )
    op.create_table(
        "roadmap_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("generation_source", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("goal_id", "version", name="uq_goal_roadmap_version"),
    )
    op.create_index("ix_roadmap_versions_goal_id", "roadmap_versions", ["goal_id"])
    op.create_index("ix_roadmap_versions_status", "roadmap_versions", ["status"])
    op.create_table(
        "roadmap_milestones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("roadmap_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["roadmap_id"], ["roadmap_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("roadmap_id", "position", name="uq_milestone_position"),
    )
    op.create_index(
        "ix_roadmap_milestones_roadmap_id", "roadmap_milestones", ["roadmap_id"]
    )
    op.create_table(
        "roadmap_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("milestone_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("completion_condition", sa.Text(), nullable=False),
        sa.Column("effort_label", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(
            ["milestone_id"], ["roadmap_milestones.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("milestone_id", "position", name="uq_step_position"),
    )
    op.create_index("ix_roadmap_steps_milestone_id", "roadmap_steps", ["milestone_id"])


def downgrade() -> None:
    op.drop_index("ix_roadmap_steps_milestone_id", table_name="roadmap_steps")
    op.drop_table("roadmap_steps")
    op.drop_index("ix_roadmap_milestones_roadmap_id", table_name="roadmap_milestones")
    op.drop_table("roadmap_milestones")
    op.drop_index("ix_roadmap_versions_status", table_name="roadmap_versions")
    op.drop_index("ix_roadmap_versions_goal_id", table_name="roadmap_versions")
    op.drop_table("roadmap_versions")
    op.drop_index("ix_goal_discovery_answers_goal_id", table_name="goal_discovery_answers")
    op.drop_table("goal_discovery_answers")
    op.drop_index("ix_goals_status", table_name="goals")
    op.drop_index("ix_goals_user_id", table_name="goals")
    op.drop_table("goals")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_token_hash", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_table("users")
