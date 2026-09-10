"""Add detailed roadmap map fields.

Revision ID: 20260910_0012
Revises: 20260902_0011
Create Date: 2026-09-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260910_0012"
down_revision: str | None = "20260902_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "roadmap_versions",
        sa.Column("strategy_summary", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "roadmap_versions",
        sa.Column("suggested_rhythm", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "roadmap_milestones",
        sa.Column("focus_areas", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "roadmap_milestones",
        sa.Column("proof_target", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "roadmap_milestones",
        sa.Column("success_signal", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("roadmap_milestones", "success_signal")
    op.drop_column("roadmap_milestones", "proof_target")
    op.drop_column("roadmap_milestones", "focus_areas")
    op.drop_column("roadmap_versions", "suggested_rhythm")
    op.drop_column("roadmap_versions", "strategy_summary")
