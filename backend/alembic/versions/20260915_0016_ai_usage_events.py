"""Add privacy-safe AI operation accounting.

Revision ID: 20260915_0016
Revises: 20260912_0015
Create Date: 2026-09-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260915_0016"
down_revision: str | None = "20260912_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=True),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("requested_provider", sa.String(length=24), nullable=False),
        sa.Column("outcome", sa.String(length=24), nullable=False),
        sa.Column("resulting_source", sa.String(length=40), nullable=False),
        sa.Column("provider_model", sa.String(length=120), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("response_count", sa.Integer(), nullable=False),
        sa.Column("failure_code", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("user_id", "goal_id", "operation", "outcome", "created_at"):
        op.create_index(f"ix_ai_usage_events_{column}", "ai_usage_events", [column])


def downgrade() -> None:
    for column in ("created_at", "outcome", "operation", "goal_id", "user_id"):
        op.drop_index(f"ix_ai_usage_events_{column}", table_name="ai_usage_events")
    op.drop_table("ai_usage_events")
