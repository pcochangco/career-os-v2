"""Allow only one in-flight roadmap generation per goal.

Revision ID: 20261117_0017
Revises: 20260915_0016
Create Date: 2026-11-17

Additive and safe on live data: a nullable column plus a partial unique index.
Existing attempts keep goal_id NULL, which the index ignores.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261117_0017"
down_revision: str | None = "20260915_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

IN_FLIGHT = "outcome = 'started' AND goal_id IS NOT NULL"


def upgrade() -> None:
    with op.batch_alter_table("roadmap_generation_attempts") as batch:
        batch.add_column(sa.Column("goal_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_generation_attempt_goal",
            "goals",
            ["goal_id"],
            ["id"],
            ondelete="CASCADE",
        )
    op.create_index(
        "uq_generation_attempt_in_flight_goal",
        "roadmap_generation_attempts",
        ["goal_id"],
        unique=True,
        postgresql_where=sa.text(IN_FLIGHT),
        sqlite_where=sa.text(IN_FLIGHT),
    )


def downgrade() -> None:
    op.drop_index("uq_generation_attempt_in_flight_goal", "roadmap_generation_attempts")
    with op.batch_alter_table("roadmap_generation_attempts") as batch:
        batch.drop_constraint("fk_generation_attempt_goal", type_="foreignkey")
        batch.drop_column("goal_id")
