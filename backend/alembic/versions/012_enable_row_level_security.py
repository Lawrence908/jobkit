"""Enable Row Level Security on all JobKit public tables (Supabase advisor).

Revision ID: 012_rls
Revises: 011_skills_spotlight

RLS applies to PostgREST (anon / authenticated JWT). The FastAPI app and
Alembic use the direct Postgres connection as superuser `postgres`, which
bypasses RLS, so API behavior is unchanged.

Frontend auth is Supabase-only; data access is via FastAPI, not direct
table queries from the browser.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "012_rls"
down_revision: Union[str, None] = "011_skills_spotlight"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All application tables in public schema (plus alembic_version).
_TABLES = (
    "alembic_version",
    "artifacts",
    "google_tokens",
    "interview_preps",
    "invite_codes",
    "job_status_events",
    "jobs",
    "profiles",
    "projects",
    "resume_bases",
    "user_skills",
)


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    for name in _TABLES:
        op.execute(sa.text(f'ALTER TABLE public."{name}" ENABLE ROW LEVEL SECURITY'))


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    for name in reversed(_TABLES):
        op.execute(sa.text(f'ALTER TABLE public."{name}" DISABLE ROW LEVEL SECURITY'))
