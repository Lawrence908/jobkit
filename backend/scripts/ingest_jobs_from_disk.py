#!/usr/bin/env python3
"""Ingest jobs from disk (jobs/*/job.json) into Postgres for a user.

Usage:
    cd backend && python -m scripts.ingest_jobs_from_disk <user_id> [--jobs-dir PATH]

Optional:
    --jobs-dir  Directory containing job folders (default: JOBKIT_JOBS_DIR from env, e.g. ./jobs)

Requires DATABASE_URL (or Postgres env) and use_postgres=True.
For each <jobs_dir>/<slug>/job.json: upserts a Job row by slug and sets user_id.
Existing jobs with the same slug are updated (url, company, role, location, keywords_json, source);
status and rejection_reason are left unchanged unless missing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Backend root on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.db.models import Job
from app.db.session import get_engine, get_session_factory, init_db
from app.services.ingest import job_json_to_markdown
from app.services import storage as storage_svc


def run(user_id: str, jobs_dir: Path) -> int:
    settings = get_settings()
    if not settings.use_postgres():
        print("Error: Postgres is required. Set DATABASE_URL (or Postgres env).")
        return 1

    jobs_dir = jobs_dir.resolve()
    if not jobs_dir.is_dir():
        print(f"Error: jobs dir is not a directory: {jobs_dir}")
        return 1

    engine = get_engine()
    init_db(engine)
    session_factory = get_session_factory(engine)
    db = session_factory()
    count_created = 0
    count_updated = 0

    try:
        # Each subdir is a job folder; expect job.json inside
        for subdir in sorted(jobs_dir.iterdir()):
            if not subdir.is_dir():
                continue
            job_json_path = subdir / "job.json"
            if not job_json_path.exists():
                continue
            try:
                data = json.loads(job_json_path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"  skip {subdir.name}: invalid job.json ({e})")
                continue

            slug = data.get("slug") or subdir.name
            if not slug:
                print(f"  skip {subdir.name}: no slug in job.json")
                continue

            existing = db.query(Job).filter(Job.slug == slug).first()
            if existing:
                # Update existing row and attach to this user if not already
                existing.user_id = user_id
                existing.url = data.get("url") or existing.url
                existing.company = (data.get("company") or "").strip() or existing.company
                existing.role = (data.get("role") or "").strip() or existing.role
                existing.location = (data.get("location") or "").strip() or existing.location
                existing.keywords_json = data.get("keywords") if data.get("keywords") is not None else existing.keywords_json
                existing.source = (data.get("source") or "").strip() or existing.source
                db.add(existing)
                count_updated += 1
            else:
                job = Job(
                    user_id=user_id,
                    url=data.get("url"),
                    company=(data.get("company") or "").strip(),
                    role=(data.get("role") or "").strip(),
                    location=(data.get("location") or "").strip(),
                    status="Have Not Applied",
                    slug=slug,
                    keywords_json=data.get("keywords"),
                    source=(data.get("source") or "").strip(),
                )
                db.add(job)
                count_created += 1

            # Optionally upload to storage so app can read job.json/job.md
            if storage_svc.use_storage() and user_id:
                try:
                    job_md = job_json_to_markdown(data)
                    storage_svc.upload_job_files(user_id, slug, data, job_md)
                except Exception:
                    pass

        db.commit()
        print(f"Jobs: {count_created} created, {count_updated} updated (from {jobs_dir}).")
        return 0
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest jobs from disk into Postgres for a user.")
    parser.add_argument("user_id", help="User UUID (e.g. 903dc38c-ec0b-4967-bf87-cab3bfc7be74)")
    parser.add_argument("--jobs-dir", type=Path, default=None, help="Jobs directory (default: JOBKIT_JOBS_DIR)")
    args = parser.parse_args()

    user_id = args.user_id.strip()
    if len(user_id) < 32:
        print(f"Error: '{user_id}' doesn't look like a UUID")
        return 1

    jobs_dir = args.jobs_dir or get_settings().jobkit_jobs_dir
    if not jobs_dir.is_absolute():
        backend = Path(__file__).resolve().parent.parent
        jobs_dir = (backend.parent / jobs_dir).resolve()

    print(f"Ingesting jobs from {jobs_dir} into user_id = {user_id}...")
    return run(user_id, jobs_dir)


if __name__ == "__main__":
    sys.exit(main())
