"""Add rejection_reason to jobs.

Revision ID: 004_add_rejection_reason
Revises: 003_add_invite_codes
Create Date: 2026-03-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004_add_rejection_reason"
down_revision: Union[str, None] = "003_add_invite_codes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("rejection_reason", sa.String(length=256), nullable=True))
    op.create_index(op.f("ix_jobs_rejection_reason"), "jobs", ["rejection_reason"], unique=False)
    # Migrate existing "New" status to new default label
    op.execute(
        sa.text("UPDATE jobs SET status = 'Have Not Applied' WHERE status = 'New'")
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_jobs_rejection_reason"), table_name="jobs")
    op.drop_column("jobs", "rejection_reason")
