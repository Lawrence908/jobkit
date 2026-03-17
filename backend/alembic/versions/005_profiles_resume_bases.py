"""Add profiles and resume_bases tables.

Revision ID: 005_profiles_resume_bases
Revises: 004_add_rejection_reason
Create Date: 2026-03-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005_profiles_resume_bases"
down_revision: Union[str, None] = "004_add_rejection_reason"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "profiles" not in tables:
        op.create_table(
            "profiles",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=256), server_default="", nullable=True),
            sa.Column("email", sa.String(length=256), server_default="", nullable=True),
            sa.Column("phone", sa.String(length=64), server_default="", nullable=True),
            sa.Column("linkedin", sa.String(length=512), server_default="", nullable=True),
            sa.Column("website", sa.String(length=512), server_default="", nullable=True),
            sa.Column("github", sa.String(length=512), server_default="", nullable=True),
            sa.Column("pitch", sa.Text(), server_default="", nullable=True),
            sa.Column("default_tone", sa.String(length=64), server_default="neutral", nullable=True),
            sa.Column("default_focus", sa.String(length=64), server_default="full-stack", nullable=True),
            sa.Column("default_length", sa.String(length=64), server_default="1 page", nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_profiles_user_id"), "profiles", ["user_id"], unique=True)

    if "resume_bases" not in tables:
        op.create_table(
            "resume_bases",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("contact", sa.JSON(), nullable=True),
            sa.Column("summary", sa.Text(), server_default="", nullable=True),
            sa.Column("highlights", sa.JSON(), nullable=True),
            sa.Column("technical_snapshot", sa.JSON(), nullable=True),
            sa.Column("experience", sa.JSON(), nullable=True),
            sa.Column("education", sa.JSON(), nullable=True),
            sa.Column("certifications", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_resume_bases_user_id"), "resume_bases", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_resume_bases_user_id"), table_name="resume_bases")
    op.drop_table("resume_bases")
    op.drop_index(op.f("ix_profiles_user_id"), table_name="profiles")
    op.drop_table("profiles")
