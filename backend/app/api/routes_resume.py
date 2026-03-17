"""Resume base API (master resume for tailoring)."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, verify_csrf
from app.db.session import get_db
from app.services.resume_base_store import get_resume_base, save_resume_base

router = APIRouter(prefix="/api/resume", tags=["resume"])


class ResumeBaseUpdate(BaseModel):
    contact: dict | None = None
    summary: str | None = None
    highlights_of_qualifications: list[str] | None = None
    technical_snapshot: dict | None = None
    experience: list[dict] | None = None
    education: list[dict] | None = None
    certifications: list[str] | None = None


@router.get("")
def read_resume(
    user_id: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return get_resume_base(user_id, db)


@router.put("")
def update_resume(
    request: Request,
    data: ResumeBaseUpdate,
    user_id: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    verify_csrf(request)
    current = get_resume_base(user_id, db)
    updates = data.model_dump(exclude_unset=True)
    for k, v in updates.items():
        if k in current:
            current[k] = v
    save_resume_base(user_id, current, db)
    return get_resume_base(user_id, db)
