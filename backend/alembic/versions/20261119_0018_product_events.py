"""Add privacy-safe product funnel events.

Revision ID: 20261119_0018
Revises: 20261117_0017
Create Date: 2026-11-19

Additive: one new table. Rows hold an event name and small enum properties only (no free
text or personal data) and cascade-delete with the account.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261119_0018"
down_revision: str | None = "20261117_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("event", sa.String(length=40), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_events_user_id", "product_events", ["user_id"])
    op.create_index(
        "ix_product_events_event_occurred", "product_events", ["event", "occurred_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_product_events_event_occurred", "product_events")
    op.drop_index("ix_product_events_user_id", "product_events")
    op.drop_table("product_events")
