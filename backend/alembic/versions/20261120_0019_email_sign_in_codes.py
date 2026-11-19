"""Add one-time email sign-in codes.

Revision ID: 20261120_0019
Revises: 20261119_0018
Create Date: 2026-11-20

Additive: one new table. Stores only a hash of each short-lived code, never the code itself.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261120_0019"
down_revision: str | None = "20261119_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_sign_in_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_sign_in_codes_email", "email_sign_in_codes", ["email"])


def downgrade() -> None:
    op.drop_index("ix_email_sign_in_codes_email", "email_sign_in_codes")
    op.drop_table("email_sign_in_codes")
