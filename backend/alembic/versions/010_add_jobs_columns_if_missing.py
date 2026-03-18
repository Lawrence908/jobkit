"""Add jobs columns from 009 if missing (safe when 009 was partially applied or stamped).

Revision ID: 010_add_jobs_columns_if_missing
Revises: 009_interview_prep_stats
Create Date: 2026-03-17

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "010_add_jobs_columns_if_missing"
down_revision: Union[str, None] = "009_interview_prep_stats"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to jobs only if they don't exist (PostgreSQL).
    # Safe when 009 was stamped but jobs table never got the new columns.
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        for col, col_type in [
            ("source_platform", "VARCHAR(64)"),
            ("work_arrangement", "VARCHAR(64)"),
            ("applied_at", "TIMESTAMP WITH TIME ZONE"),
            ("first_response_at", "TIMESTAMP WITH TIME ZONE"),
            ("interview_at", "TIMESTAMP WITH TIME ZONE"),
            ("rejected_at", "TIMESTAMP WITH TIME ZONE"),
            ("offered_at", "TIMESTAMP WITH TIME ZONE"),
            ("withdrawn_at", "TIMESTAMP WITH TIME ZONE"),
        ]:
            conn.execute(text(f'ALTER TABLE jobs ADD COLUMN IF NOT EXISTS "{col}" {col_type}'))
    else:
        # SQLite: no IF NOT EXISTS for columns; check and add
        from sqlalchemy import inspect
        import sqlalchemy as sa
        insp = inspect(conn)
        existing = {c["name"] for c in insp.get_columns("jobs")}
        if "source_platform" not in existing:
            op.add_column("jobs", sa.Column("source_platform", sa.String(64), nullable=True))
        if "work_arrangement" not in existing:
            op.add_column("jobs", sa.Column("work_arrangement", sa.String(64), nullable=True))
        if "applied_at" not in existing:
            op.add_column("jobs", sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True))
        if "first_response_at" not in existing:
            op.add_column("jobs", sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True))
        if "interview_at" not in existing:
            op.add_column("jobs", sa.Column("interview_at", sa.DateTime(timezone=True), nullable=True))
        if "rejected_at" not in existing:
            op.add_column("jobs", sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True))
        if "offered_at" not in existing:
            op.add_column("jobs", sa.Column("offered_at", sa.DateTime(timezone=True), nullable=True))
        if "withdrawn_at" not in existing:
            op.add_column("jobs", sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Optional: drop columns. Omitted so we don't break DBs that rely on them.
    pass
