"""Add alternate resource refresh attempt ledger.

Revision ID: 20260901_0008
Revises: 20260831_0007
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260901_0008"
down_revision: str | None = "20260831_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roadmap_step_resource_refresh_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("step_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["step_id"], ["roadmap_steps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_roadmap_step_resource_refresh_attempts_user_id",
        "roadmap_step_resource_refresh_attempts",
        ["user_id"],
    )
    op.create_index(
        "ix_roadmap_step_resource_refresh_attempts_step_id",
        "roadmap_step_resource_refresh_attempts",
        ["step_id"],
    )
    op.create_index(
        "ix_roadmap_step_resource_refresh_attempts_created_at",
        "roadmap_step_resource_refresh_attempts",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_roadmap_step_resource_refresh_attempts_created_at",
        table_name="roadmap_step_resource_refresh_attempts",
    )
    op.drop_index(
        "ix_roadmap_step_resource_refresh_attempts_step_id",
        table_name="roadmap_step_resource_refresh_attempts",
    )
    op.drop_index(
        "ix_roadmap_step_resource_refresh_attempts_user_id",
        table_name="roadmap_step_resource_refresh_attempts",
    )
    op.drop_table("roadmap_step_resource_refresh_attempts")
