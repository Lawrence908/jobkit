"""Initial schema: jobs, artifacts, google_tokens.

Revision ID: 001_initial
Revises:
Create Date: 2025-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("company", sa.String(length=512), nullable=True, server_default=""),
        sa.Column("role", sa.String(length=512), nullable=True, server_default=""),
        sa.Column("location", sa.String(length=512), nullable=True, server_default=""),
        sa.Column("status", sa.String(length=64), nullable=True, server_default="New"),
        sa.Column("slug", sa.String(length=256), nullable=False),
        sa.Column("keywords_json", sa.JSON(), nullable=True),
        sa.Column("source", sa.String(length=128), nullable=True, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jobs_company"), "jobs", ["company"], unique=False)
    op.create_index(op.f("ix_jobs_role"), "jobs", ["role"], unique=False)
    op.create_index(op.f("ix_jobs_slug"), "jobs", ["slug"], unique=True)
    op.create_index(op.f("ix_jobs_status"), "jobs", ["status"], unique=False)
    op.create_index(op.f("ix_jobs_url"), "jobs", ["url"], unique=False)

    op.create_table(
        "artifacts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("drive_file_id", sa.String(length=256), nullable=True),
        sa.Column("drive_link", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_artifacts_job_id"), "artifacts", ["job_id"], unique=False)
    op.create_index(op.f("ix_artifacts_type"), "artifacts", ["type"], unique=False)

    op.create_table(
        "google_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True, server_default="google"),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=False),
        sa.Column("scopes", sa.String(length=1024), nullable=True, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", name="uq_google_tokens_provider"),
    )
    op.create_index(op.f("ix_google_tokens_provider"), "google_tokens", ["provider"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_google_tokens_provider"), table_name="google_tokens")
    op.drop_table("google_tokens")
    op.drop_index(op.f("ix_artifacts_type"), table_name="artifacts")
    op.drop_index(op.f("ix_artifacts_job_id"), table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_index(op.f("ix_jobs_url"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_status"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_slug"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_role"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_company"), table_name="jobs")
    op.drop_table("jobs")
