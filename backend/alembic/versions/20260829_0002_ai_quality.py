"""Add AI roadmap quality and provenance fields.

Revision ID: 20260829_0002
Revises: 20260829_0001
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260829_0002"
down_revision: str | None = "20260829_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "roadmap_versions",
        sa.Column("goal_outcome", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "roadmap_versions",
        sa.Column("starting_state_summary", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "roadmap_versions",
        sa.Column("assumptions", sa.JSON(), server_default="[]", nullable=False),
    )
    op.add_column(
        "roadmap_versions",
        sa.Column("schema_version", sa.String(length=20), server_default="1.0", nullable=False),
    )
    op.add_column(
        "roadmap_versions",
        sa.Column(
            "provider_model",
            sa.String(length=120),
            server_default="deterministic-fixture",
            nullable=False,
        ),
    )
    op.add_column(
        "roadmap_versions",
        sa.Column("prompt_version", sa.String(length=120), server_default="", nullable=False),
    )
    op.add_column(
        "roadmap_versions",
        sa.Column("provider_response_ids", sa.JSON(), server_default="[]", nullable=False),
    )
    op.add_column(
        "roadmap_versions",
        sa.Column("input_snapshot", sa.JSON(), server_default="{}", nullable=False),
    )
    op.add_column(
        "roadmap_versions",
        sa.Column("quality_report", sa.JSON(), server_default="{}", nullable=False),
    )
    op.add_column(
        "roadmap_versions",
        sa.Column("quality_score", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "roadmap_versions",
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "roadmap_versions",
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "roadmap_versions",
        sa.Column("generation_duration_ms", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "roadmap_milestones",
        sa.Column("rationale", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "roadmap_steps",
        sa.Column("stable_key", sa.String(length=64), server_default="legacy-step", nullable=False),
    )
    op.create_index("ix_roadmap_steps_stable_key", "roadmap_steps", ["stable_key"])
    op.add_column(
        "roadmap_steps",
        sa.Column("rationale", sa.Text(), server_default="", nullable=False),
    )
    op.alter_column(
        "roadmap_steps",
        "effort_label",
        existing_type=sa.String(length=40),
        type_=sa.String(length=80),
        existing_nullable=False,
    )
    op.add_column(
        "roadmap_steps",
        sa.Column("evidence_suggestion", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "roadmap_steps",
        sa.Column("prerequisite_step_keys", sa.JSON(), server_default="[]", nullable=False),
    )
    op.add_column(
        "roadmap_steps",
        sa.Column("resource_queries", sa.JSON(), server_default="[]", nullable=False),
    )
    op.create_table(
        "roadmap_step_dependencies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("step_id", sa.Uuid(), nullable=False),
        sa.Column("prerequisite_step_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["step_id"], ["roadmap_steps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["prerequisite_step_id"],
            ["roadmap_steps.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("step_id", "prerequisite_step_id", name="uq_step_prerequisite"),
    )
    op.create_index(
        "ix_roadmap_step_dependencies_step_id",
        "roadmap_step_dependencies",
        ["step_id"],
    )
    op.create_index(
        "ix_roadmap_step_dependencies_prerequisite_step_id",
        "roadmap_step_dependencies",
        ["prerequisite_step_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_roadmap_step_dependencies_prerequisite_step_id",
        table_name="roadmap_step_dependencies",
    )
    op.drop_index(
        "ix_roadmap_step_dependencies_step_id",
        table_name="roadmap_step_dependencies",
    )
    op.drop_table("roadmap_step_dependencies")
    op.drop_column("roadmap_steps", "resource_queries")
    op.drop_column("roadmap_steps", "prerequisite_step_keys")
    op.drop_column("roadmap_steps", "evidence_suggestion")
    op.alter_column(
        "roadmap_steps",
        "effort_label",
        existing_type=sa.String(length=80),
        type_=sa.String(length=40),
        existing_nullable=False,
    )
    op.drop_column("roadmap_steps", "rationale")
    op.drop_index("ix_roadmap_steps_stable_key", table_name="roadmap_steps")
    op.drop_column("roadmap_steps", "stable_key")
    op.drop_column("roadmap_milestones", "rationale")
    op.drop_column("roadmap_versions", "generation_duration_ms")
    op.drop_column("roadmap_versions", "output_tokens")
    op.drop_column("roadmap_versions", "input_tokens")
    op.drop_column("roadmap_versions", "quality_score")
    op.drop_column("roadmap_versions", "quality_report")
    op.drop_column("roadmap_versions", "input_snapshot")
    op.drop_column("roadmap_versions", "provider_response_ids")
    op.drop_column("roadmap_versions", "prompt_version")
    op.drop_column("roadmap_versions", "provider_model")
    op.drop_column("roadmap_versions", "schema_version")
    op.drop_column("roadmap_versions", "assumptions")
    op.drop_column("roadmap_versions", "starting_state_summary")
    op.drop_column("roadmap_versions", "goal_outcome")
