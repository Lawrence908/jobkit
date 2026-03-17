"""Add user_skills and projects tables.

Revision ID: 006_user_skills_projects
Revises: 005_profiles_resume_bases
Create Date: 2026-03-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006_user_skills_projects"
down_revision: Union[str, None] = "005_profiles_resume_bases"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "user_skills" not in tables:
        op.create_table(
            "user_skills",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("categories", sa.JSON(), nullable=True),
            sa.Column("items", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_user_skills_user_id"), "user_skills", ["user_id"], unique=True)

    if "projects" not in tables:
        op.create_table(
            "projects",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=256), server_default="", nullable=True),
            sa.Column("description", sa.Text(), server_default="", nullable=True),
            sa.Column("link", sa.String(length=512), server_default="", nullable=True),
            sa.Column("status", sa.String(length=128), server_default="", nullable=True),
            sa.Column("dates", sa.String(length=128), server_default="", nullable=True),
            sa.Column("tags", sa.JSON(), nullable=True),
            sa.Column("tech_stack", sa.JSON(), nullable=True),
            sa.Column("bullets", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_projects_user_id"), "projects", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_projects_user_id"), table_name="projects")
    op.drop_table("projects")
    op.drop_index(op.f("ix_user_skills_user_id"), table_name="user_skills")
    op.drop_table("user_skills")
