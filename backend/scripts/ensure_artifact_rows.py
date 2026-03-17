#!/usr/bin/env python3
"""Ensure artifact rows exist for all generated files (resume.md, cover_letter.md, notes.md, PDFs).

For each job of the given user, checks storage and disk for generated files and
creates/updates artifact rows so the UI shows download links and Drive upload can find them.
Run after upload_generated_to_storage or when jobs have generated content but no artifact rows.

Usage:
    cd backend && python -m scripts.ensure_artifact_rows <user_id> [--dry-run]
    python -m scripts.ensure_artifact_rows <user_id> --jobs-dir /path/to/jobs --outputs-dir /path/to/outputs

Requires DATABASE_URL. Storage (SUPABASE_*) optional; will fall back to disk checks.
Source paths: --jobs-dir and --outputs-dir, or JOBKIT_JOBS_DIR and JOBKIT_OUTPUTS_DIR from env.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.db.models import Artifact, Job
from app.db.session import get_engine, get_session_factory, init_db
from app.services import storage as storage_svc
from app.utils.files import ensure_safe_relative_path

# (artifact_type, filename in generated/ or outputs/)
GENERATED_MD = [
    ("resume_md", "resume.md"),
    ("cover_letter_md", "cover_letter.md"),
    ("notes_md", "notes.md"),
]
GENERATED_PDF = [
    ("resume_pdf", "resume.pdf"),
    ("cover_letter_pdf", "cover_letter.pdf"),
]


def _file_exists_storage(user_id: str, slug: str, filename: str, is_pdf: bool) -> bool:
    if not storage_svc.use_storage() or not user_id:
        return False
    try:
        key = storage_svc.generated_key(user_id, slug, filename)
        storage_svc.download_bytes(key)
        return True
    except Exception:
        return False


def _file_exists_disk(
    slug: str, filename: str, is_pdf: bool, jobs_dir: Path, outputs_dir: Path
) -> bool:
    if is_pdf:
        path = ensure_safe_relative_path(outputs_dir, slug, filename)
    else:
        path = ensure_safe_relative_path(jobs_dir, slug, "generated", filename)
    return path.exists()


def ensure_artifacts_for_job(db, job: Job, jobs_dir: Path, outputs_dir: Path, dry_run: bool) -> int:
    """Create/update artifact rows for this job from existing generated files. Returns count updated."""
    user_id = job.user_id or ""
    slug = job.slug
    count = 0
    for art_type, filename in GENERATED_MD + GENERATED_PDF:
        is_pdf = filename.endswith(".pdf")
        exists = _file_exists_storage(user_id, slug, filename, is_pdf) or _file_exists_disk(
            slug, filename, is_pdf, jobs_dir, outputs_dir
        )
        if not exists:
            continue
        path_str = storage_svc.generated_key(user_id, slug, filename) if user_id else (
            f"outputs/{slug}/{filename}" if is_pdf else f"{slug}/generated/{filename}"
        )
        existing = db.query(Artifact).filter(Artifact.job_id == job.id, Artifact.type == art_type).first()
        if existing:
            if existing.path != path_str:
                existing.path = path_str
                existing.user_id = user_id or existing.user_id
                db.add(existing)
                count += 1
                if dry_run:
                    print(f"  would update artifact job_id={job.id} type={art_type} -> {path_str}")
        else:
            if dry_run:
                print(f"  would add artifact job_id={job.id} type={art_type} -> {path_str}")
            else:
                db.add(Artifact(job_id=job.id, user_id=user_id or None, type=art_type, path=path_str))
            count += 1
    return count


def run(user_id: str, dry_run: bool, jobs_dir: Path | None, outputs_dir: Path | None) -> int:
    settings = get_settings()
    if not settings.use_postgres():
        print("Error: Postgres required. Set DATABASE_URL.")
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

        total = 0
        for job in jobs:
            n = ensure_artifacts_for_job(db, job, jobs_dir, outputs_dir, dry_run)
            total += n
        if not dry_run and total:
            db.commit()
        if dry_run:
            print(f"Would ensure {total} artifact row(s). Run without --dry-run to apply.")
        else:
            print(f"Ensured {total} artifact row(s).")
        return 0
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure artifact rows for generated files.")
    parser.add_argument("user_id", help="User UUID")
    parser.add_argument("--dry-run", action="store_true", help="Only print what would be done")
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
