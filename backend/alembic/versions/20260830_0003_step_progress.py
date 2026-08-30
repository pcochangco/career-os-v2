"""Add explicit roadmap step progress.

Revision ID: 20260830_0003
Revises: 20260829_0002
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_0003"
down_revision: str | None = "20260829_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roadmap_step_progress",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("step_id", sa.Uuid(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["step_id"], ["roadmap_steps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "step_id", name="uq_user_step_progress"),
    )
    op.create_index(
        "ix_roadmap_step_progress_step_id",
        "roadmap_step_progress",
        ["step_id"],
    )
    op.create_index(
        "ix_roadmap_step_progress_user_id",
        "roadmap_step_progress",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_roadmap_step_progress_user_id", table_name="roadmap_step_progress")
    op.drop_index("ix_roadmap_step_progress_step_id", table_name="roadmap_step_progress")
    op.drop_table("roadmap_step_progress")
