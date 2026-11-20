"""Track roadmap generation progress.

Revision ID: 20261121_0020
Revises: 20261120_0019
Create Date: 2026-11-21

Additive: three columns with defaults, so existing rows and older code keep working.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261121_0020"
down_revision: str | None = "20261120_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "roadmap_generation_attempts",
        sa.Column("progress_stage", sa.String(length=120), nullable=False, server_default=""),
    )
    op.add_column(
        "roadmap_generation_attempts",
        sa.Column("progress_done", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "roadmap_generation_attempts",
        sa.Column("progress_total", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("roadmap_generation_attempts", "progress_total")
    op.drop_column("roadmap_generation_attempts", "progress_done")
    op.drop_column("roadmap_generation_attempts", "progress_stage")
