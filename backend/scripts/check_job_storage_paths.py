#!/usr/bin/env python3
"""Compare jobs table to disk and (optionally) storage paths.

For each job, prints slug, expected storage key for generated/resume.md,
and whether that file exists on disk and/or in Supabase Storage.
Use to verify path alignment and why some jobs return 400.

Usage:
    cd backend && python -m scripts.check_job_storage_paths [--jobs-dir PATH]
    With SUPABASE_* set, also checks storage (one GET per job).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.db.models import Job
from app.db.session import get_engine, get_session_factory, init_db
from app.services import storage as storage_svc
from app.utils.files import ensure_safe_relative_path


def run(jobs_dir: Path | None) -> int:
    settings = get_settings()
    if not settings.use_postgres():
        print("Error: Postgres required. Set DATABASE_URL.")
        return 1

    if jobs_dir is None:
        jobs_dir = settings.jobkit_jobs_dir
    if not jobs_dir.is_absolute():
        backend = Path(__file__).resolve().parent.parent
        jobs_dir = (backend.parent / jobs_dir).resolve()

    engine = get_engine()
    init_db(engine)
    session_factory = get_session_factory(engine)
    db = session_factory()

    try:
        jobs = db.query(Job).filter(Job.user_id.isnot(None)).order_by(Job.id).all()
        if not jobs:
            print("No jobs with user_id found.")
            return 0

        user_id = jobs[0].user_id
        check_storage = storage_svc.use_storage()

        print(f"Jobs dir: {jobs_dir}")
        print(f"Storage:  {'yes' if check_storage else 'no (set SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY to check)'}")
        print()
        print(f"{'id':<4} {'slug (truncated)':<52} {'disk':<6} {'storage':<8}  storage key")
        print("-" * 120)

        for job in jobs:
            key = storage_svc.generated_key(job.user_id or "", job.slug, "resume.md")
            disk_path = ensure_safe_relative_path(jobs_dir, job.slug, "generated", "resume.md")
            on_disk = disk_path.exists()
            in_storage = False
            if check_storage and job.user_id:
                try:
                    storage_svc.download_bytes(key)
                    in_storage = True
                except Exception:
                    pass
            slug_short = (job.slug[:49] + "…") if len(job.slug) > 52 else job.slug
            print(f"{job.id:<4} {slug_short:<52} {str(on_disk):<6} {str(in_storage):<8}  {key}")

        return 0
    finally:
        db.close()


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Compare jobs table to disk and storage paths.")
    parser.add_argument("--jobs-dir", type=Path, default=None)
    args = parser.parse_args()
    return run(args.jobs_dir)


if __name__ == "__main__":
    sys.exit(main())
