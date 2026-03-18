"""Load and save personalization profile (contact, pitch, defaults). DB-backed when use_postgres else YAML."""
import logging
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Profile
from app.services.avatar_store import has_avatar as user_has_avatar

logger = logging.getLogger(__name__)

_DEFAULT_PROFILE: dict[str, Any] = {
    "name": "",
    "email": "",
    "phone": "",
    "linkedin": "",
    "website": "",
    "github": "",
    "pitch": "",
    "default_tone": "neutral",
    "default_focus": "full-stack",
    "default_length": "1 page",
    "llm_provider": "openrouter",
    "llm_api_key": "",
    "llm_model": "anthropic/claude-sonnet-4.6",
    "llm_temperature": 0.2,
    "google_drive_root_folder_id": "",
    "google_sheets_spreadsheet_id": "",
    "google_sheets_tab_name": "",
    "google_sheets_url_column": "",
}


def _profile_path() -> Path:
    return get_settings().jobkit_data_dir / "profile.yml"


def _row_to_profile(row: Profile) -> dict[str, Any]:
    return {
        "name": row.name or "",
        "email": row.email or "",
        "phone": row.phone or "",
        "linkedin": row.linkedin or "",
        "website": row.website or "",
        "github": row.github or "",
        "pitch": row.pitch or "",
        "default_tone": row.default_tone or "neutral",
        "default_focus": row.default_focus or "full-stack",
        "default_length": row.default_length or "1 page",
        "llm_provider": getattr(row, "llm_provider", None) or "openrouter",
        "llm_api_key": getattr(row, "llm_api_key", None) or "",
        "llm_model": getattr(row, "llm_model", None) or "anthropic/claude-sonnet-4.6",
        "llm_temperature": float(getattr(row, "llm_temperature", 0.2) or 0.2),
        "google_drive_root_folder_id": getattr(row, "google_drive_root_folder_id", None) or "",
        "google_sheets_spreadsheet_id": getattr(row, "google_sheets_spreadsheet_id", None) or "",
        "google_sheets_tab_name": getattr(row, "google_sheets_tab_name", None) or "",
        "google_sheets_url_column": getattr(row, "google_sheets_url_column", None) or "",
    }


def get_profile(user_id: str, db: Session | None = None) -> dict[str, Any]:
    """Load profile for user. When use_postgres and db given, use DB (create default row if missing). Else load from profile.yml."""
    settings = get_settings()
    if settings.use_postgres() and db is not None:
        row = db.query(Profile).filter(Profile.user_id == user_id).first()
        if row:
            p = _row_to_profile(row)
            p["has_avatar"] = user_has_avatar(user_id)
            return p
        row = Profile(
            user_id=user_id,
            name=_DEFAULT_PROFILE["name"],
            email=_DEFAULT_PROFILE["email"],
            phone=_DEFAULT_PROFILE["phone"],
            linkedin=_DEFAULT_PROFILE["linkedin"],
            website=_DEFAULT_PROFILE["website"],
            github=_DEFAULT_PROFILE["github"],
            pitch=_DEFAULT_PROFILE["pitch"],
            default_tone=_DEFAULT_PROFILE["default_tone"],
            default_focus=_DEFAULT_PROFILE["default_focus"],
            default_length=_DEFAULT_PROFILE["default_length"],
            llm_provider=_DEFAULT_PROFILE["llm_provider"],
            llm_api_key=_DEFAULT_PROFILE["llm_api_key"],
            llm_model=_DEFAULT_PROFILE["llm_model"],
            llm_temperature=_DEFAULT_PROFILE["llm_temperature"],
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        p = _row_to_profile(row)
        p["has_avatar"] = user_has_avatar(user_id)
        return p
    path = _profile_path()
    if not path.exists():
        o = _DEFAULT_PROFILE.copy()
        o["has_avatar"] = user_has_avatar(user_id)
        return o
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        out = _DEFAULT_PROFILE.copy()
        for k in out:
            if k in data and data[k] is not None:
                out[k] = data[k]
        out["has_avatar"] = user_has_avatar(user_id)
        return out
    except Exception as e:
        logger.warning("Failed to load profile %s: %s", path, e)
        o = _DEFAULT_PROFILE.copy()
        o["has_avatar"] = user_has_avatar(user_id)
        return o


def save_profile(user_id: str, profile: dict[str, Any], db: Session | None = None) -> None:
    """Save profile for user. When use_postgres and db given, upsert DB row. Else write profile.yml."""
    settings = get_settings()
    if settings.use_postgres() and db is not None:
        row = db.query(Profile).filter(Profile.user_id == user_id).first()
        data = {k: profile.get(k, _DEFAULT_PROFILE.get(k, "")) for k in _DEFAULT_PROFILE}
        if row:
            row.name = data["name"]
            row.email = data["email"]
            row.phone = data["phone"]
            row.linkedin = data["linkedin"]
            row.website = data["website"]
            row.github = data["github"]
            row.pitch = data["pitch"]
            row.default_tone = data["default_tone"]
            row.default_focus = data["default_focus"]
            row.default_length = data["default_length"]
            row.llm_provider = data["llm_provider"]
            row.llm_api_key = data["llm_api_key"]
            row.llm_model = data["llm_model"]
            row.llm_temperature = data["llm_temperature"]
            row.google_drive_root_folder_id = (data.get("google_drive_root_folder_id") or "").strip() or None
            row.google_sheets_spreadsheet_id = (data.get("google_sheets_spreadsheet_id") or "").strip() or None
            row.google_sheets_tab_name = (data.get("google_sheets_tab_name") or "").strip() or None
            row.google_sheets_url_column = (data.get("google_sheets_url_column") or "").strip() or None
            db.add(row)
        else:
            row = Profile(user_id=user_id, **data)
            row.google_drive_root_folder_id = (data.get("google_drive_root_folder_id") or "").strip() or None
            row.google_sheets_spreadsheet_id = (data.get("google_sheets_spreadsheet_id") or "").strip() or None
            row.google_sheets_tab_name = (data.get("google_sheets_tab_name") or "").strip() or None
            row.google_sheets_url_column = (data.get("google_sheets_url_column") or "").strip() or None
            db.add(row)
        db.commit()
        return
    path = _profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {k: profile.get(k, _DEFAULT_PROFILE[k]) for k in _DEFAULT_PROFILE}
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
