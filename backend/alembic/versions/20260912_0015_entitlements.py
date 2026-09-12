"""Add account tiers and a non-destructive free-roadmap boundary.

Revision ID: 20260912_0015
Revises: 20260911_0014
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260912_0015"
down_revision: str | None = "20260911_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "subscription_tier",
            sa.String(length=16),
            nullable=False,
            server_default="free",
        ),
    )
    op.create_index("ix_users_subscription_tier", "users", ["subscription_tier"])
    op.add_column(
        "roadmap_versions",
        sa.Column(
            "free_access_milestones",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("roadmap_versions", "free_access_milestones")
    op.drop_index("ix_users_subscription_tier", table_name="users")
    op.drop_column("users", "subscription_tier")
