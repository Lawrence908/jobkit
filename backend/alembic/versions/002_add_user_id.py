"""Add user_id to jobs, artifacts, google_tokens for multi-user support.

Revision ID: 002_add_user_id
Revises: 001_initial
Create Date: 2026-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002_add_user_id"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("user_id", sa.String(36), nullable=True))
    op.create_index(op.f("ix_jobs_user_id"), "jobs", ["user_id"], unique=False)

    op.add_column("artifacts", sa.Column("user_id", sa.String(36), nullable=True))
    op.create_index(op.f("ix_artifacts_user_id"), "artifacts", ["user_id"], unique=False)

    op.add_column("google_tokens", sa.Column("user_id", sa.String(36), nullable=True))
    op.create_index(op.f("ix_google_tokens_user_id"), "google_tokens", ["user_id"], unique=False)
    # Replace the single-user unique constraint on provider with a per-user one
    op.drop_constraint("uq_google_tokens_provider", "google_tokens", type_="unique")
    op.drop_index("ix_google_tokens_provider", table_name="google_tokens")
    op.create_index(
        "ix_google_tokens_user_provider",
        "google_tokens",
        ["user_id", "provider"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_google_tokens_user_provider", table_name="google_tokens")
    op.create_index(op.f("ix_google_tokens_provider"), "google_tokens", ["provider"], unique=True)
    op.create_unique_constraint("uq_google_tokens_provider", "google_tokens", ["provider"])
    op.drop_index(op.f("ix_google_tokens_user_id"), table_name="google_tokens")
    op.drop_column("google_tokens", "user_id")

    op.drop_index(op.f("ix_artifacts_user_id"), table_name="artifacts")
    op.drop_column("artifacts", "user_id")

    op.drop_index(op.f("ix_jobs_user_id"), table_name="jobs")
    op.drop_column("jobs", "user_id")
