"""Personalization profile API (contact, pitch, defaults for resume/cover)."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.core.auth import get_current_user, verify_csrf
from app.services.profile_store import get_profile, save_profile

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    pitch: str | None = None
    default_tone: str | None = None
    default_focus: str | None = None
    default_length: str | None = None


@router.get("")
def read_profile(
    _: Annotated[str, Depends(get_current_user)],
):
    return get_profile()


@router.put("")
def update_profile(
    request: Request,
    data: ProfileUpdate,
    _: Annotated[str, Depends(get_current_user)],
):
    verify_csrf(request)
    profile = get_profile()
    updates = data.model_dump(exclude_unset=True)
    for k, v in updates.items():
        if k in profile:
            profile[k] = v
    save_profile(profile)
    return get_profile()
