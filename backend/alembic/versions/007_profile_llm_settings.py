"""Add LLM provider settings to profiles (provider, api_key, model, temperature).

Revision ID: 007_profile_llm_settings
Revises: 006_user_skills_projects
Create Date: 2026-03-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "007_profile_llm_settings"
down_revision: Union[str, None] = "006_user_skills_projects"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("llm_provider", sa.String(length=64), server_default="openrouter", nullable=True))
    op.add_column("profiles", sa.Column("llm_api_key", sa.Text(), server_default="", nullable=True))
    op.add_column("profiles", sa.Column("llm_model", sa.String(length=256), server_default="anthropic/claude-sonnet-4.7", nullable=True))
    op.add_column("profiles", sa.Column("llm_temperature", sa.Float(), server_default="0.2", nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "llm_temperature")
    op.drop_column("profiles", "llm_model")
    op.drop_column("profiles", "llm_api_key")
    op.drop_column("profiles", "llm_provider")
