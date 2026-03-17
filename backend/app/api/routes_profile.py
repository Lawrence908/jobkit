"""Personalization profile API (contact, pitch, defaults for resume/cover)."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, verify_csrf
from app.db.session import get_db
from app.services.profile_store import get_profile, save_profile

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    website: str | None = None
    github: str | None = None
    pitch: str | None = None
    default_tone: str | None = None
    default_focus: str | None = None
    default_length: str | None = None
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_temperature: float | None = None
    google_drive_root_folder_id: str | None = None
    google_sheets_spreadsheet_id: str | None = None
    google_sheets_tab_name: str | None = None
    google_sheets_url_column: str | None = None


@router.get("")
def read_profile(
    user_id: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return get_profile(user_id, db)


@router.put("")
def update_profile(
    request: Request,
    data: ProfileUpdate,
    user_id: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    verify_csrf(request)
    profile = get_profile(user_id, db)
    updates = data.model_dump(exclude_unset=True)
    for k, v in updates.items():
        if k in profile:
            profile[k] = v
    save_profile(user_id, profile, db)
    return get_profile(user_id, db)
