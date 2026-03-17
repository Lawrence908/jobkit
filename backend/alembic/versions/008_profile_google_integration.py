"""Add per-user Google integration fields to profiles (drive folder, sheet id, tab, url column).

Revision ID: 008_profile_google_integration
Revises: 007_profile_llm_settings
Create Date: 2026-03-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "008_profile_google_integration"
down_revision: Union[str, None] = "007_profile_llm_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("google_drive_root_folder_id", sa.String(length=128), nullable=True))
    op.add_column("profiles", sa.Column("google_sheets_spreadsheet_id", sa.String(length=128), nullable=True))
    op.add_column("profiles", sa.Column("google_sheets_tab_name", sa.String(length=256), nullable=True))
    op.add_column("profiles", sa.Column("google_sheets_url_column", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "google_sheets_url_column")
    op.drop_column("profiles", "google_sheets_tab_name")
    op.drop_column("profiles", "google_sheets_spreadsheet_id")
    op.drop_column("profiles", "google_drive_root_folder_id")
