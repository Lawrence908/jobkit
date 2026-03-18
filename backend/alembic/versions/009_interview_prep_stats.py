"""Interview prep and stats: job timestamps, job_status_events, interview_preps.

Revision ID: 009_interview_prep_stats
Revises: 008_profile_google_integration
Create Date: 2026-03-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "009_interview_prep_stats"
down_revision: Union[str, None] = "008_profile_google_integration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New columns on jobs
    op.add_column("jobs", sa.Column("source_platform", sa.String(length=64), nullable=True))
    op.add_column("jobs", sa.Column("work_arrangement", sa.String(length=64), nullable=True))
    op.add_column("jobs", sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("interview_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("offered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True))

    # job_status_events table
    op.create_table(
        "job_status_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("old_status", sa.String(length=64), nullable=True),
        sa.Column("new_status", sa.String(length=64), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_job_status_events_job_id"), "job_status_events", ["job_id"], unique=False)
    op.create_index(op.f("ix_job_status_events_user_id"), "job_status_events", ["user_id"], unique=False)

    # interview_preps table
    op.create_table(
        "interview_preps",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), default=1, nullable=False),
        sa.Column("markdown_text", sa.Text(), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.Column("source_resume_artifact_id", sa.Integer(), nullable=True),
        sa.Column("source_cover_letter_artifact_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_resume_artifact_id"], ["artifacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_cover_letter_artifact_id"], ["artifacts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_interview_preps_job_id"), "interview_preps", ["job_id"], unique=False)
    op.create_index(op.f("ix_interview_preps_user_id"), "interview_preps", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_interview_preps_user_id"), table_name="interview_preps")
    op.drop_index(op.f("ix_interview_preps_job_id"), table_name="interview_preps")
    op.drop_table("interview_preps")

    op.drop_index(op.f("ix_job_status_events_user_id"), table_name="job_status_events")
    op.drop_index(op.f("ix_job_status_events_job_id"), table_name="job_status_events")
    op.drop_table("job_status_events")

    op.drop_column("jobs", "withdrawn_at")
    op.drop_column("jobs", "offered_at")
    op.drop_column("jobs", "rejected_at")
    op.drop_column("jobs", "interview_at")
    op.drop_column("jobs", "first_response_at")
    op.drop_column("jobs", "applied_at")
    op.drop_column("jobs", "work_arrangement")
    op.drop_column("jobs", "source_platform")
