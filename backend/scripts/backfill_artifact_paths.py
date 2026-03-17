#!/usr/bin/env python3
"""Backfill artifact.path to storage-key form (user_id/jobs/...).

Existing rows may have path like slug/generated/resume.md or outputs/slug/file.pdf.
This script updates them to user_id/jobs/slug/generated/... when artifact.user_id
is set, so all artifacts for a job live under the same folder (job + generated + PDFs).

Usage:
    cd backend && python -m scripts.backfill_artifact_paths [--dry-run]

Requires DATABASE_URL and use_postgres=True.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.models import Artifact
from app.db.session import get_engine, get_session_factory, init_db
from app.core.config import get_settings
from app.services.storage import is_storage_key


def run(dry_run: bool) -> int:
    settings = get_settings()
    if not settings.use_postgres():
        print("Error: Postgres required. Set DATABASE_URL.")
        return 1

    engine = get_engine()
    init_db(engine)
    session_factory = get_session_factory(engine)
    db = session_factory()
    updated = 0

    try:
        for art in db.query(Artifact).filter(Artifact.user_id.isnot(None)).all():
            if not art.path or is_storage_key(art.path):
                continue
            user_id = art.user_id or ""
            if art.path.startswith("outputs/"):
                # outputs/slug/resume.pdf -> user_id/jobs/slug/generated/resume.pdf
                rest = art.path[len("outputs/"):]
                if "/" in rest:
                    slug, filename = rest.split("/", 1)
                    new_path = f"{user_id}/jobs/{slug}/generated/{filename}"
                else:
                    new_path = f"{user_id}/outputs/{art.path[len('outputs/'):]}"
            else:
                # slug/generated/resume.md etc.
                new_path = f"{user_id}/jobs/{art.path}"
            art.path = new_path
            db.add(art)
            updated += 1
            if dry_run:
                print(f"  would update artifact id={art.id} type={art.type} -> {new_path}")
        if not dry_run and updated:
            db.commit()
            print(f"Updated {updated} artifact paths to storage-key form.")
        elif dry_run:
            print(f"Would update {updated} artifact paths (run without --dry-run to apply).")
        else:
            print("No artifact paths needed updating.")
        return 0
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill artifact paths to user_id/jobs/.../generated/...")
    parser.add_argument("--dry-run", action="store_true", help="Only print what would be updated")
    args = parser.parse_args()
    return run(args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
