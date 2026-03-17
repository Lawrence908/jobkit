#!/usr/bin/env python3
"""Upload existing generated files and PDFs from disk to Supabase Storage.

Puts everything for a job under one folder: user_id/jobs/<slug>/ (job.json, job.md)
and user_id/jobs/<slug>/generated/ (resume.md, cover_letter.md, notes.md, resume.pdf, cover_letter.pdf).

Usage:
    cd backend && python -m scripts.upload_generated_to_storage <user_id> [--dry-run]
    python -m scripts.upload_generated_to_storage <user_id> --jobs-dir /path/to/jobs --outputs-dir /path/to/outputs

Requires: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DATABASE_URL, and supabase package.
Source paths: --jobs-dir and --outputs-dir, or JOBKIT_JOBS_DIR and JOBKIT_OUTPUTS_DIR from env.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.db.models import Job
from app.db.session import get_engine, get_session_factory, init_db
from app.services.ingest import job_json_to_markdown
from app.services import storage as storage_svc
from app.utils.files import ensure_safe_relative_path
from scripts.ensure_artifact_rows import ensure_artifacts_for_job


def run(user_id: str, dry_run: bool, jobs_dir: Path | None, outputs_dir: Path | None) -> int:
    settings = get_settings()
    if not settings.use_postgres():
        print("Error: Postgres required. Set DATABASE_URL.")
        return 1
    if not storage_svc.use_storage():
        print("Error: Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY for storage.")
        return 1

    if jobs_dir is None:
        jobs_dir = settings.jobkit_jobs_dir
    if outputs_dir is None:
        outputs_dir = settings.jobkit_outputs_dir
    if not jobs_dir.is_absolute():
        backend = Path(__file__).resolve().parent.parent
        jobs_dir = (backend.parent / jobs_dir).resolve()
    if not outputs_dir.is_absolute():
        backend = Path(__file__).resolve().parent.parent
        outputs_dir = (backend.parent / outputs_dir).resolve()

    print(f"Using jobs_dir={jobs_dir}  outputs_dir={outputs_dir}")

    engine = get_engine()
    init_db(engine)
    session_factory = get_session_factory(engine)
    db = session_factory()

    try:
        jobs = db.query(Job).filter(Job.user_id == user_id).all()
        if not jobs:
            print(f"No jobs found for user_id {user_id}.")
            return 0

        uploaded = 0
        for job in jobs:
            slug = job.slug
            # Job folder on disk
            job_dir = ensure_safe_relative_path(jobs_dir, slug)
            gen_dir = job_dir / "generated"
            out_dir = ensure_safe_relative_path(outputs_dir, slug)

            # job.json + job.md
            for name, key_fn, content_fn in [
                ("job.json", lambda: storage_svc.job_json_key(user_id, slug), lambda: json.dumps(json.loads((job_dir / "job.json").read_text(encoding="utf-8")), indent=2)),
                ("job.md", lambda: storage_svc.job_md_key(user_id, slug), lambda: (job_dir / "job.md").read_text(encoding="utf-8")),
            ]:
                path = job_dir / name
                if not path.exists():
                    continue
                key = key_fn()
                if dry_run:
                    print(f"  would upload {path} -> {key}")
                    uploaded += 1
                else:
                    try:
                        if name == "job.json":
                            storage_svc.upload_bytes(key, content_fn().encode("utf-8"), "application/json")
                        else:
                            storage_svc.upload_bytes(key, content_fn().encode("utf-8"), "text/markdown")
                        uploaded += 1
                    except Exception as e:
                        print(f"  skip {key}: {e}")

            # generated/*.md
            for fname in ("resume.md", "cover_letter.md", "notes.md"):
                path = gen_dir / fname
                if not path.exists():
                    continue
                key = storage_svc.generated_key(user_id, slug, fname)
                if dry_run:
                    print(f"  would upload {path} -> {key}")
                    uploaded += 1
                else:
                    try:
                        storage_svc.upload_bytes(key, path.read_bytes(), "text/markdown")
                        uploaded += 1
                    except Exception as e:
                        print(f"  skip {key}: {e}")

            # outputs/<slug>/*.pdf -> same job folder (generated/)
            if out_dir.exists():
                for pdf_path in out_dir.glob("*.pdf"):
                    key = storage_svc.generated_key(user_id, slug, pdf_path.name)
                    if dry_run:
                        print(f"  would upload {pdf_path} -> {key}")
                        uploaded += 1
                    else:
                        try:
                            storage_svc.upload_bytes(key, pdf_path.read_bytes(), "application/pdf")
                            uploaded += 1
                        except Exception as e:
                            print(f"  skip {key}: {e}")

            # Ensure artifact rows so generated docs are tracked (download links, Drive upload)
            if not dry_run:
                ensure_artifacts_for_job(db, job, jobs_dir, outputs_dir, dry_run=False)

        if not dry_run:
            db.commit()
        if dry_run:
            print(f"Would upload {uploaded} files. Run without --dry-run to apply.")
        else:
            print(f"Uploaded {uploaded} files to bucket {storage_svc.BUCKET}.")
        return 0
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload generated files and PDFs from disk to Supabase Storage.")
    parser.add_argument("user_id", help="User UUID")
    parser.add_argument("--dry-run", action="store_true", help="Only print what would be uploaded")
    parser.add_argument("--jobs-dir", type=Path, default=None, help="Path to jobs dir (default: JOBKIT_JOBS_DIR)")
    parser.add_argument("--outputs-dir", type=Path, default=None, help="Path to outputs dir (default: JOBKIT_OUTPUTS_DIR)")
    args = parser.parse_args()
    user_id = args.user_id.strip()
    if len(user_id) < 32:
        print("Error: user_id should be a UUID.")
        return 1
    return run(user_id, args.dry_run, args.jobs_dir, args.outputs_dir)


if __name__ == "__main__":
    sys.exit(main())
