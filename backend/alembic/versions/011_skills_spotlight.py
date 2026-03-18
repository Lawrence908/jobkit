"""Add skills_spotlight to user_skills for profile card curation.

Revision ID: 011_skills_spotlight
Revises: 010_add_jobs_columns_if_missing
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_skills_spotlight"
down_revision: Union[str, None] = "010_add_jobs_columns_if_missing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.add_column("user_skills", sa.Column("skills_spotlight", sa.JSON(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.drop_column("user_skills", "skills_spotlight")
