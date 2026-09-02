"""Add authenticated beta issue reports.

Revision ID: 20260902_0011
Revises: 20260901_0010
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260902_0011"
down_revision: str | None = "20260901_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "issue_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("request_reference", sa.String(length=100), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("app_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_issue_reports_user_id", "issue_reports", ["user_id"])
    op.create_index("ix_issue_reports_category", "issue_reports", ["category"])
    op.create_index("ix_issue_reports_created_at", "issue_reports", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_issue_reports_created_at", table_name="issue_reports")
    op.drop_index("ix_issue_reports_category", table_name="issue_reports")
    op.drop_index("ix_issue_reports_user_id", table_name="issue_reports")
    op.drop_table("issue_reports")
