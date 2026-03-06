"""Load and hold canonical resume + projects data from YAML."""
import logging
from pathlib import Path
from typing import Any

import yaml

from app.core.config import get_settings

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


def get_projects() -> list[dict[str, Any]]:
    return _projects


def get_skills() -> dict[str, Any] | list[Any]:
    return _skills


def get_loaded_at() -> float | None:
    return _loaded_at
