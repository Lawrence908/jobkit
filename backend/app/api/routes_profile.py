"""Personalization profile API (contact, pitch, defaults for resume/cover)."""
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, verify_csrf
from app.db.session import get_db
from app.services.avatar_store import delete_avatar, read_avatar_bytes, save_avatar_from_upload
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


@router.get("/avatar")
def get_profile_avatar(
    user_id: Annotated[str, Depends(get_current_user)],
):
    """Private JPEG for the signed-in user (profile UI only—not auto-injected into resume PDFs)."""
    data = read_avatar_bytes(user_id)
    if not data:
        raise HTTPException(status_code=404, detail="No avatar")
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.post("/avatar")
async def upload_profile_avatar(
    request: Request,
    user_id: Annotated[str, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    verify_csrf(request)
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    try:
        save_avatar_from_upload(user_id, raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "has_avatar": True}


@router.delete("/avatar")
def delete_profile_avatar(
    request: Request,
    user_id: Annotated[str, Depends(get_current_user)],
):
    verify_csrf(request)
    delete_avatar(user_id)
    return {"ok": True, "has_avatar": False}
