"""Add persisted adaptive discovery questions.

Revision ID: 20260831_0007
Revises: 20260830_0006
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260831_0007"
down_revision: str | None = "20260830_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "goal_discovery_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("question_key", sa.String(length=64), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("help_text", sa.Text(), nullable=False),
        sa.Column("selection_mode", sa.String(length=16), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("placeholder", sa.String(length=180), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("goal_id", "revision", "question_key", name="uq_goal_question_revision_key"),
        sa.UniqueConstraint("goal_id", "revision", "position", name="uq_goal_question_revision_position"),
    )
    op.create_index("ix_goal_discovery_questions_goal_id", "goal_discovery_questions", ["goal_id"])
    op.create_index("ix_goal_discovery_questions_status", "goal_discovery_questions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_goal_discovery_questions_status", table_name="goal_discovery_questions")
    op.drop_index("ix_goal_discovery_questions_goal_id", table_name="goal_discovery_questions")
    op.drop_table("goal_discovery_questions")
