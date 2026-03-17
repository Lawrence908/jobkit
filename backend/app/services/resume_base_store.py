"""Load and save resume base (master resume). DB-backed when use_postgres else YAML."""
import logging
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import ResumeBase

logger = logging.getLogger(__name__)


def _resume_path() -> Path:
    return get_settings().jobkit_data_dir / "resume_base.yml"


def _row_to_resume_base(row: ResumeBase) -> dict[str, Any]:
    """Convert DB row to truth_store-style dict (highlights_of_qualifications for LLM compatibility)."""
    out: dict[str, Any] = {
        "contact": row.contact or {},
        "summary": row.summary or "",
        "highlights_of_qualifications": row.highlights or [],
        "technical_snapshot": row.technical_snapshot or {},
        "experience": row.experience or [],
        "education": row.education or [],
        "certifications": row.certifications or [],
    }
    return out


def _default_resume_base() -> dict[str, Any]:
    return {
        "contact": {},
        "summary": "",
        "highlights_of_qualifications": [],
        "technical_snapshot": {},
        "experience": [],
        "education": [],
        "certifications": [],
    }


def get_resume_base(user_id: str, db: Session | None = None) -> dict[str, Any]:
    """Load resume base for user. When use_postgres and db, use DB (create default row if missing). Else load from resume_base.yml."""
    settings = get_settings()
    if settings.use_postgres() and db is not None:
        row = db.query(ResumeBase).filter(ResumeBase.user_id == user_id).first()
        if row:
            return _row_to_resume_base(row)
        row = ResumeBase(user_id=user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
        return _row_to_resume_base(row)
    path = _resume_path()
    if not path.exists():
        return _default_resume_base()
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
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
    except Exception as e:
        logger.warning("Failed to load resume_base %s: %s", path, e)
        return _default_resume_base()


def save_resume_base(user_id: str, data: dict[str, Any], db: Session | None = None) -> None:
    """Save resume base for user. When use_postgres and db, upsert DB row. Else write resume_base.yml."""
    settings = get_settings()
    highlights = data.get("highlights_of_qualifications", data.get("highlights", []))
    if settings.use_postgres() and db is not None:
        row = db.query(ResumeBase).filter(ResumeBase.user_id == user_id).first()
        payload = {
            "contact": data.get("contact") or {},
            "summary": data.get("summary") or "",
            "highlights": highlights if isinstance(highlights, list) else [],
            "technical_snapshot": data.get("technical_snapshot") or {},
            "experience": data.get("experience") if isinstance(data.get("experience"), list) else [],
            "education": data.get("education") if isinstance(data.get("education"), list) else [],
            "certifications": data.get("certifications") if isinstance(data.get("certifications"), list) else [],
        }
        if row:
            row.contact = payload["contact"]
            row.summary = payload["summary"]
            row.highlights = payload["highlights"]
            row.technical_snapshot = payload["technical_snapshot"]
            row.experience = payload["experience"]
            row.education = payload["education"]
            row.certifications = payload["certifications"]
            db.add(row)
        else:
            db.add(ResumeBase(user_id=user_id, **payload))
        db.commit()
        return
    path = _resume_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "contact": data.get("contact") or {},
        "summary": data.get("summary") or "",
        "highlights_of_qualifications": highlights if isinstance(highlights, list) else [],
        "technical_snapshot": data.get("technical_snapshot") or {},
        "experience": data.get("experience") or [],
        "education": data.get("education") or [],
        "certifications": data.get("certifications") or [],
    }
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(out, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
