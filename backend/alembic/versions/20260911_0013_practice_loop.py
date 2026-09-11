"""Add optional roadmap practice prompts.

Revision ID: 20260911_0013
Revises: 20260910_0012
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260911_0013"
down_revision: str | None = "20260910_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "roadmap_versions",
        sa.Column("practice_tasks", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("roadmap_versions", "practice_tasks")
