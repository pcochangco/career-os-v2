"""Store one optional practice completion per user and roadmap day.

Revision ID: 20260911_0014
Revises: 20260911_0013
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260911_0014"
down_revision: str | None = "20260911_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roadmap_practice_completions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("roadmap_id", sa.Uuid(), nullable=False),
        sa.Column("practice_date", sa.Date(), nullable=False),
        sa.Column("task_index", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["roadmap_id"], ["roadmap_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "roadmap_id", "practice_date", name="uq_practice_completion_day"),
    )
    op.create_index(
        "ix_roadmap_practice_completions_user_id",
        "roadmap_practice_completions",
        ["user_id"],
    )
    op.create_index(
        "ix_roadmap_practice_completions_roadmap_id",
        "roadmap_practice_completions",
        ["roadmap_id"],
    )
    op.create_index(
        "ix_roadmap_practice_completions_practice_date",
        "roadmap_practice_completions",
        ["practice_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_roadmap_practice_completions_practice_date")
    op.drop_index("ix_roadmap_practice_completions_roadmap_id")
    op.drop_index("ix_roadmap_practice_completions_user_id")
    op.drop_table("roadmap_practice_completions")
