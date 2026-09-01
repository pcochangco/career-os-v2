"""Add learner resource feedback.

Revision ID: 20260901_0009
Revises: 20260901_0008
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260901_0009"
down_revision: str | None = "20260901_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roadmap_step_resource_feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("step_id", sa.Uuid(), nullable=False),
        sa.Column("resource_url", sa.String(length=2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["step_id"], ["roadmap_steps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "step_id", "resource_url", name="uq_user_step_resource_feedback"
        ),
    )
    op.create_index(
        "ix_roadmap_step_resource_feedback_user_id",
        "roadmap_step_resource_feedback",
        ["user_id"],
    )
    op.create_index(
        "ix_roadmap_step_resource_feedback_step_id",
        "roadmap_step_resource_feedback",
        ["step_id"],
    )
    op.create_index(
        "ix_roadmap_step_resource_feedback_created_at",
        "roadmap_step_resource_feedback",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_roadmap_step_resource_feedback_created_at",
        table_name="roadmap_step_resource_feedback",
    )
    op.drop_index(
        "ix_roadmap_step_resource_feedback_step_id",
        table_name="roadmap_step_resource_feedback",
    )
    op.drop_index(
        "ix_roadmap_step_resource_feedback_user_id",
        table_name="roadmap_step_resource_feedback",
    )
    op.drop_table("roadmap_step_resource_feedback")
