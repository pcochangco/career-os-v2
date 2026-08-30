"""Add the AI generation attempt ledger.

Revision ID: 20260830_0006
Revises: 20260830_0005
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_0006"
down_revision: str | None = "20260830_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roadmap_generation_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("requested_provider", sa.String(length=24), nullable=False),
        sa.Column("outcome", sa.String(length=24), nullable=False),
        sa.Column("resulting_source", sa.String(length=40), nullable=False),
        sa.Column("provider_model", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_roadmap_generation_attempts_user_id",
        "roadmap_generation_attempts",
        ["user_id"],
    )
    op.create_index(
        "ix_roadmap_generation_attempts_outcome",
        "roadmap_generation_attempts",
        ["outcome"],
    )
    op.create_index(
        "ix_roadmap_generation_attempts_created_at",
        "roadmap_generation_attempts",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_roadmap_generation_attempts_created_at",
        table_name="roadmap_generation_attempts",
    )
    op.drop_index(
        "ix_roadmap_generation_attempts_outcome",
        table_name="roadmap_generation_attempts",
    )
    op.drop_index(
        "ix_roadmap_generation_attempts_user_id",
        table_name="roadmap_generation_attempts",
    )
    op.drop_table("roadmap_generation_attempts")
