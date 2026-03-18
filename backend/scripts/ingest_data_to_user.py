#!/usr/bin/env python3
"""Ingest profile, resume, skills, projects, and jobs into a user in Postgres.

Usage:
    cd backend && python -m scripts.ingest_data_to_user 903dc38c-ec0b-4967-bf87-cab3bfc7be74

Optional:
    python -m scripts.ingest_data_to_user <user_id> [--data-dir PATH]
    python -m scripts.ingest_data_to_user <user_id> --project-yml path/to/project.yml
      (ingest only that project; paths are relative to your current working directory)

Requires DATABASE_URL (or Postgres env) and use_postgres=True.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

# Backend root on sys.path so app imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.db.models import Job, Project, ResumeBase, UserSkills
from app.db.session import get_engine, get_session_factory, init_db
from app.services.profile_store import save_profile
from app.services.resume_base_store import _default_resume_base, save_resume_base


def _load_yaml(path: Path) -> dict[str, Any] | list[Any]:
    if not path.exists():
        return {} if "projects" not in str(path) else []
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _resume_base_from_path(path: Path) -> dict[str, Any]:
    """Build resume_base dict from a YAML file (same shape as resume_base_store file load)."""
    data = _load_yaml(path)
    if isinstance(data, list):
        return _default_resume_base()
    out = _default_resume_base()
    if "contact" in data and isinstance(data["contact"], dict):
        out["contact"] = data["contact"]
    if "summary" in data and data["summary"] is not None:
        out["summary"] = str(data["summary"])
    if "highlights_of_qualifications" in data and isinstance(data["highlights_of_qualifications"], list):
        out["highlights_of_qualifications"] = data["highlights_of_qualifications"]
    if "technical_snapshot" in data and isinstance(data["technical_snapshot"], dict):
        out["technical_snapshot"] = data["technical_snapshot"]
    if "experience" in data and isinstance(data["experience"], list):
        out["experience"] = data["experience"]
    if "education" in data and isinstance(data["education"], list):
        out["education"] = data["education"]
    if "certifications" in data and isinstance(data["certifications"], list):
        out["certifications"] = data["certifications"]
    return out


def _skills_from_path(path: Path) -> tuple[dict[str, list[str]], list[str]]:
    """Return (categories, items) from skills.yml."""
    data = _load_yaml(path)
    if isinstance(data, list):
        return {}, data if isinstance(data, list) else []
    categories = data.get("categories")
    if not isinstance(categories, dict):
        categories = {}
    # Normalize to str -> list[str]
    out_cats: dict[str, list[str]] = {}
    for k, v in categories.items():
        out_cats[str(k)] = list(v) if isinstance(v, list) else []
    items = data.get("items")
    if not isinstance(items, list):
        items = []
    return out_cats, [str(x) for x in items]


def _project_from_yaml(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize a single project YAML dict to DB shape."""
    return {
        "name": str(data.get("name") or ""),
        "description": str(data.get("description") or ""),
        "link": str(data.get("link") or ""),
        "status": str(data.get("status") or ""),
        "dates": str(data.get("dates") or ""),
        "tags": list(data["tags"]) if isinstance(data.get("tags"), list) else [],
        "tech_stack": list(data["tech_stack"]) if isinstance(data.get("tech_stack"), list) else [],
        "bullets": list(data["bullets"]) if isinstance(data.get("bullets"), list) else [],
    }


def run(user_id: str, data_dir: Path) -> None:
    settings = get_settings()
    if not settings.use_postgres():
        print("Error: Postgres is required. Set DATABASE_URL (or Postgres env).")
        sys.exit(1)

    engine = get_engine()
    init_db(engine)
    session_factory = get_session_factory(engine)
    db = session_factory()

    try:
        # Profile
        profile_path = data_dir / "profile.yml"
        if profile_path.exists():
            profile_data = _load_yaml(profile_path)
            if isinstance(profile_data, dict) and profile_data:
                save_profile(user_id, profile_data, db)
                print(f"  profile: ingested from {profile_path.name}")
            else:
                print(f"  profile: skipped (empty or invalid: {profile_path})")
        else:
            print(f"  profile: skipped (not found: {profile_path})")

        # Resume base
        resume_path = data_dir / "resume_base.yml"
        if resume_path.exists():
            resume_data = _resume_base_from_path(resume_path)
            save_resume_base(user_id, resume_data, db)
            print(f"  resume_base: ingested from {resume_path.name}")
        else:
            print(f"  resume_base: skipped (not found: {resume_path})")

        # Skills
        skills_path = data_dir / "skills.yml"
        if skills_path.exists():
            categories, items = _skills_from_path(skills_path)
            row = db.query(UserSkills).filter(UserSkills.user_id == user_id).first()
            if row:
                row.categories = categories
                row.items = items
                db.add(row)
            else:
                db.add(UserSkills(user_id=user_id, categories=categories, items=items))
            db.commit()
            print(f"  skills: ingested from {skills_path.name} ({len(categories)} categories, {len(items)} flat items)")
        else:
            print(f"  skills: skipped (not found: {skills_path})")

        # Projects (only *.yml) — upsert by name
        projects_dir = data_dir / "projects"
        if projects_dir.is_dir():
            created, updated = 0, 0
            for f in sorted(projects_dir.glob("*.yml")):
                data = _load_yaml(f)
                if isinstance(data, dict) and data:
                    payload = _project_from_yaml(data)
                    existing = (
                        db.query(Project)
                        .filter(Project.user_id == user_id, Project.name == payload["name"])
                        .first()
                    )
                    if existing:
                        for k, v in payload.items():
                            setattr(existing, k, v)
                        updated += 1
                    else:
                        db.add(Project(user_id=user_id, **payload))
                        created += 1
            if created or updated:
                db.commit()
                print(f"  projects: {created} created, {updated} updated from projects/*.yml")
            else:
                print(f"  projects: no .yml files found in {projects_dir}")
        else:
            print(f"  projects: skipped (no directory: {projects_dir})")

        # Jobs (jobs/jobs.json — array of job objects)
        jobs_file = data_dir / "jobs" / "jobs.json"
        if jobs_file.exists():
            with open(jobs_file, encoding="utf-8") as f:
                jobs_data = json.load(f)
            if isinstance(jobs_data, list):
                count = 0
                for jd in jobs_data:
                    if not isinstance(jd, dict):
                        continue
                    existing = db.query(Job).filter(Job.slug == jd.get("slug", "")).first()
                    if existing:
                        continue
                    job = Job(
                        user_id=user_id,
                        url=jd.get("url") or "",
                        company=jd.get("company") or "",
                        role=jd.get("role") or "",
                        location=jd.get("location") or "",
                        status=jd.get("status") or "Have Not Applied",
                        rejection_reason=jd.get("rejection_reason"),
                        slug=jd.get("slug") or "",
                        keywords_json=jd.get("keywords"),
                        source=jd.get("source") or "",
                        source_platform=jd.get("source_platform"),
                        work_arrangement=jd.get("work_arrangement"),
                    )
                    db.add(job)
                    count += 1
                if count:
                    db.commit()
                    print(f"  jobs: ingested {count} from {jobs_file.name}")
                else:
                    print(f"  jobs: all jobs already exist (skipped)")
            else:
                print(f"  jobs: skipped (not a JSON array: {jobs_file})")
        else:
            print(f"  jobs: skipped (not found: {jobs_file})")

        print("Done.")
    finally:
        db.close()


def run_projects_only(user_id: str, project_paths: list[Path]) -> None:
    """Insert Project rows from standalone YAML files (no profile/resume/skills/jobs)."""
    settings = get_settings()
    if not settings.use_postgres():
        print("Error: Postgres is required. Set DATABASE_URL (or Postgres env).")
        sys.exit(1)

    engine = get_engine()
    init_db(engine)
    session_factory = get_session_factory(engine)
    db = session_factory()

    try:
        count = 0
        for f in project_paths:
            data = _load_yaml(f)
            if not isinstance(data, dict) or not data:
                print(f"  skipped (empty or invalid): {f}")
                continue
            payload = _project_from_yaml(data)
            db.add(Project(user_id=user_id, **payload))
            count += 1
        if count:
            db.commit()
            print(f"  projects: ingested {count} file(s)")
        else:
            print("  projects: nothing ingested")
        print("Done.")
    finally:
        db.close()


def _resolve_cli_path(p: Path) -> Path:
    """Resolve path relative to cwd (not repo root), so ../data/... from backend/ works."""
    if p.is_absolute():
        return p.resolve()
    return (Path.cwd() / p).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest data/ YAML files into a user in Postgres.")
    parser.add_argument("user_id", help="User UUID (e.g. 903dc38c-ec0b-4967-bf87-cab3bfc7be74)")
    parser.add_argument("--data-dir", type=Path, default=None, help="Data directory (default: JOBKIT_DATA_DIR)")
    parser.add_argument(
        "--project-yml",
        action="append",
        dest="project_yml",
        default=None,
        metavar="PATH",
        help="Ingest only this project YAML (repeatable). Paths are relative to cwd. No --data-dir needed.",
    )
    args = parser.parse_args()

    user_id = args.user_id.strip()
    if len(user_id) < 32:
        print(f"Error: '{user_id}' doesn't look like a UUID")
        sys.exit(1)

    if args.project_yml:
        paths = [_resolve_cli_path(Path(p)) for p in args.project_yml]
        for p in paths:
            if not p.exists():
                print(f"Error: project file not found: {p}")
                sys.exit(1)
            if not p.is_file():
                print(f"Error: not a file: {p}")
                sys.exit(1)
        print(f"Ingesting {len(paths)} project file(s) into user_id = {user_id}...")
        run_projects_only(user_id, paths)
        return

    data_dir = args.data_dir or get_settings().jobkit_data_dir
    if not data_dir.is_absolute():
        data_dir = _resolve_cli_path(data_dir)
    else:
        data_dir = data_dir.resolve()
    if not data_dir.exists():
        print(f"Error: data dir does not exist: {data_dir}")
        sys.exit(1)

    print(f"Ingesting data from {data_dir} into user_id = {user_id}...")
    run(user_id, data_dir)


if __name__ == "__main__":
    main()
