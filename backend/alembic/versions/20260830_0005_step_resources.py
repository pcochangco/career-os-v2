"""Add verified roadmap step resources.

Revision ID: 20260830_0005
Revises: 20260830_0004
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_0005"
down_revision: str | None = "20260830_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roadmap_step_resources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("step_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("resource_type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("source_name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("why_relevant", sa.Text(), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=2048), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["step_id"], ["roadmap_steps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("step_id", "url", name="uq_step_resource_url"),
    )
    op.create_index(
        "ix_roadmap_step_resources_step_id",
        "roadmap_step_resources",
        ["step_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_roadmap_step_resources_step_id",
        table_name="roadmap_step_resources",
    )
    op.drop_table("roadmap_step_resources")
