"""Load and hold canonical resume + projects data from YAML. When use_postgres and db/user_id given, read from DB."""
import logging
from pathlib import Path
from typing import Any, TYPE_CHECKING

import yaml

from app.core.config import get_settings

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_resume_base: dict[str, Any] = {}
_projects: list[dict[str, Any]] = []
_skills: dict[str, Any] | list[Any] = {}
_loaded_at: float | None = None


def _load_yaml(path: Path) -> dict[str, Any] | list[Any]:
    if not path.exists():
        return {} if "projects" not in str(path) else []
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning("Failed to load %s: %s", path, e)
        return {} if "projects" not in str(path) else []


def load_truth_store() -> None:
    """Load resume_base.yml, projects/*.yml, skills.yml from JOBKIT_DATA_DIR."""
    global _resume_base, _projects, _skills, _loaded_at
    import time
    settings = get_settings()
    data_dir = settings.jobkit_data_dir
    resume_path = data_dir / "resume_base.yml"
    skills_path = data_dir / "skills.yml"
    projects_dir = data_dir / "projects"
    _resume_base = _load_yaml(resume_path)
    if isinstance(_resume_base, list):
        _resume_base = {}
    _skills = _load_yaml(skills_path)
    if isinstance(_skills, list):
        _skills = {"items": _skills}
    _projects = []
    if projects_dir.is_dir():
        for f in sorted(projects_dir.glob("*.yml")):
            data = _load_yaml(f)
            if isinstance(data, dict):
                _projects.append(data)
            elif isinstance(data, list):
                _projects.extend(data)
    _loaded_at = time.time()
    logger.info("Truth store loaded: resume_base=%s, projects=%d", bool(_resume_base), len(_projects))


def get_resume_base() -> dict[str, Any]:
    return _resume_base


def get_projects(user_id: str | None = None, db: "Session | None" = None) -> list[dict[str, Any]]:
    if user_id and db is not None and get_settings().use_postgres():
        from app.db.models import Project
        rows = db.query(Project).filter(Project.user_id == user_id).order_by(Project.id).all()
        return [
            {
                "name": p.name or "",
                "description": p.description or "",
                "link": p.link or "",
                "status": p.status or "",
                "dates": p.dates or "",
                "tags": p.tags or [],
                "tech_stack": p.tech_stack or [],
                "bullets": p.bullets or [],
            }
            for p in rows
        ]
    return _projects


def get_skills(user_id: str | None = None, db: "Session | None" = None) -> dict[str, Any] | list[Any]:
    if user_id and db is not None and get_settings().use_postgres():
        from app.db.models import UserSkills
        row = db.query(UserSkills).filter(UserSkills.user_id == user_id).first()
        if row:
            return {"categories": row.categories or {}, "items": row.items or []}
        return {"categories": {}, "items": []}
    return _skills


def get_loaded_at() -> float | None:
    return _loaded_at
