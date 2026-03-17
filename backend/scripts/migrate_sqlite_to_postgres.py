#!/usr/bin/env python3
"""
One-time data migration: copy jobs, artifacts, google_tokens from SQLite to Postgres (Supabase).

Usage:
  From backend dir, with .env containing DATABASE_URL (Postgres):
    python scripts/migrate_sqlite_to_postgres.py [path/to/jobkit.db]

  If path omitted, uses JOBKIT_DATA_DIR/jobkit.db (from env or default /app/data).

Prerequisites:
  - Supabase tables already created (alembic upgrade head with DATABASE_URL set).
  - SQLite file exists and is readable.
"""
import os
import sys
from pathlib import Path

# Add backend root for app imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.db.models import Job, Artifact, GoogleToken


def get_sqlite_path() -> Path:
    settings = get_settings()
    return settings.db_path


def main() -> None:
    settings = get_settings()
    if not settings.use_postgres():
        print("Set DATABASE_URL (or DATABASE_HOST + DATABASE_PASSWORD) in .env for Postgres.", file=sys.stderr)
        sys.exit(1)
    db_url = settings.database_url

    sqlite_path = Path(sys.argv[1]) if len(sys.argv) > 1 else get_sqlite_path()
    if not sqlite_path.exists():
        print(f"SQLite file not found: {sqlite_path}", file=sys.stderr)
        sys.exit(1)

    sqlite_url = f"sqlite:///{sqlite_path}"
    pg_engine = create_engine(db_url)
    sqlite_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

    SessionSqlite = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)
    SessionPg = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)

    with SessionSqlite() as src, SessionPg() as dst:
        # Copy jobs (do not set id; let Postgres serial assign)
        jobs = src.query(Job).order_by(Job.id).all()
        id_map = {}  # old job id -> new job id
        for j in jobs:
            new_j = Job(
                url=j.url,
                company=j.company or "",
                role=j.role or "",
                location=j.location or "",
                status=j.status or "New",
                slug=j.slug,
                keywords_json=j.keywords_json,
                source=j.source or "",
                created_at=j.created_at,
                updated_at=j.updated_at,
            )
            dst.add(new_j)
            dst.flush()  # so new_j.id is set
            id_map[j.id] = new_j.id
        dst.commit()
        print(f"Copied {len(jobs)} jobs.")

        # Copy artifacts (use new job_id from id_map)
        artifacts = src.query(Artifact).order_by(Artifact.id).all()
        for a in artifacts:
            new_job_id = id_map.get(a.job_id)
            if new_job_id is None:
                continue
            new_a = Artifact(
                job_id=new_job_id,
                type=a.type,
                path=a.path,
                drive_file_id=a.drive_file_id,
                drive_link=a.drive_link,
                created_at=a.created_at,
            )
            dst.add(new_a)
        dst.commit()
        print(f"Copied {len(artifacts)} artifacts.")

        # Copy google_tokens (single row typically)
        tokens = src.query(GoogleToken).all()
        for t in tokens:
            new_t = GoogleToken(
                provider=t.provider or "google",
                encrypted_refresh_token=t.encrypted_refresh_token,
                scopes=t.scopes or "",
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            dst.add(new_t)
        dst.commit()
        print(f"Copied {len(tokens)} google_tokens.")

        # Ensure Postgres sequences are ahead of max id for future inserts
        for table, col in [("jobs", "id"), ("artifacts", "id"), ("google_tokens", "id")]:
            result = dst.execute(text(f"SELECT COALESCE(MAX({col}), 0) FROM {table}"))
            max_id = result.scalar()
            dst.execute(
                text("SELECT setval(pg_get_serial_sequence(:t, :c), :m)"),
                {"t": table, "c": col, "m": max_id},
            )
        dst.commit()
        print("Sequences updated.")


if __name__ == "__main__":
    main()
