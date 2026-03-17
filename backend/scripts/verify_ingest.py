#!/usr/bin/env python3
"""Verify DB contents for a user match the data/ YAML files (after ingest_data_to_user).

Usage:
    python backend/scripts/verify_ingest.py 903dc38c-ec0b-4967-bf87-cab3bfc7be74 [--data-dir data/]

Requires DATABASE_URL and use_postgres=True.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from app.core.config import get_settings
from app.db.models import Project, ResumeBase, UserSkills
from app.db.session import get_engine, get_session_factory, init_db
from app.services.resume_base_store import _default_resume_base
from scripts.ingest_data_to_user import (
    _load_yaml,
    _project_from_yaml,
    _resume_base_from_path,
    _skills_from_path,
)


def run(user_id: str, data_dir: Path) -> bool:
    settings = get_settings()
    if not settings.use_postgres():
        print("Error: Postgres required. Set DATABASE_URL.")
        return False

    engine = get_engine()
    init_db(engine)
    session_factory = get_session_factory(engine)
    db = session_factory()
    ok = True

    try:
        # Resume
        resume_path = data_dir / "resume_base.yml"
        if resume_path.exists():
            file_data = _resume_base_from_path(resume_path)
            row = db.query(ResumeBase).filter(ResumeBase.user_id == user_id).first()
            if not row:
                print("  resume_bases: MISSING row for user")
                ok = False
            else:
                from app.services.resume_base_store import _row_to_resume_base
                db_data = _row_to_resume_base(row)
                checks = [
                    (db_data.get("contact", {}).get("name"), file_data.get("contact", {}).get("name"), "contact.name"),
                    (len(db_data.get("highlights_of_qualifications", [])), len(file_data.get("highlights_of_qualifications", [])), "highlights count"),
                    (len(db_data.get("technical_snapshot", {})), len(file_data.get("technical_snapshot", {})), "technical_snapshot keys"),
                    (len(db_data.get("experience", [])), len(file_data.get("experience", [])), "experience count"),
                    (len(db_data.get("education", [])), len(file_data.get("education", [])), "education count"),
                    (len(db_data.get("certifications", [])), len(file_data.get("certifications", [])), "certifications count"),
                ]
                for db_val, file_val, label in checks:
                    if db_val != file_val:
                        print(f"  resume_bases: {label} DB={db_val} file={file_val} MISMATCH")
                        ok = False
                if ok:
                    print("  resume_bases: OK (contact, highlights, technical_snapshot, experience, education, certifications match file)")
        else:
            print("  resume_bases: skipped (no resume_base.yml)")

        # Skills
        skills_path = data_dir / "skills.yml"
        if skills_path.exists():
            file_cats, file_items = _skills_from_path(skills_path)
            row = db.query(UserSkills).filter(UserSkills.user_id == user_id).first()
            if not row:
                print("  user_skills: MISSING row for user")
                ok = False
            else:
                db_cats = row.categories or {}
                db_items = row.items or []
                if len(db_cats) != len(file_cats) or len(db_items) != len(file_items):
                    print(f"  user_skills: DB categories={len(db_cats)} items={len(db_items)}  file categories={len(file_cats)} items={len(file_items)} MISMATCH")
                    ok = False
                else:
                    print(f"  user_skills: OK ({len(db_cats)} categories, {len(db_items)} items)")
        else:
            print("  user_skills: skipped (no skills.yml)")

        # Projects
        projects_dir = data_dir / "projects"
        if projects_dir.is_dir():
            file_ymls = sorted(projects_dir.glob("*.yml"))
            db_rows = db.query(Project).filter(Project.user_id == user_id).order_by(Project.name).all()
            if len(db_rows) != len(file_ymls):
                print(f"  projects: DB count={len(db_rows)}  file .yml count={len(file_ymls)} MISMATCH")
                ok = False
            else:
                file_names = []
                for f in file_ymls:
                    d = _load_yaml(f)
                    if isinstance(d, dict) and d:
                        file_names.append(_project_from_yaml(d).get("name") or "")
                db_names = [r.name or "" for r in db_rows]
                if sorted(db_names) != sorted(file_names):
                    print("  projects: name list mismatch")
                    ok = False
                else:
                    print(f"  projects: OK ({len(db_rows)} projects, names match)")
        else:
            print("  projects: skipped (no data/projects dir)")

        return ok
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("user_id", help="User UUID")
    parser.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args()

    user_id = args.user_id.strip()
    data_dir = args.data_dir or get_settings().jobkit_data_dir
    if not data_dir.is_absolute():
        # Resolve relative to repo root (parent of backend)
        data_dir = (_backend.parent / data_dir).resolve()
    if not data_dir.exists():
        print(f"Error: data dir not found: {data_dir}")
        sys.exit(1)

    print(f"Verifying DB vs {data_dir} for user_id = {user_id}")
    if run(user_id, data_dir):
        print("Verification passed.")
    else:
        print("Verification had mismatches.")
        sys.exit(1)


if __name__ == "__main__":
    main()
