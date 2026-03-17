"""Skills API (categorized + flat items for tailoring)."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, verify_csrf
from app.db.session import get_db
from app.db.models import UserSkills
from app.core.config import get_settings

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillsUpdate(BaseModel):
    categories: dict[str, list[str]] | None = None
    items: list[str] | None = None


def _row_to_skills(row: UserSkills) -> dict:
    return {
        "categories": row.categories or {},
        "items": row.items or [],
    }


@router.get("")
def read_skills(
    user_id: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if not get_settings().use_postgres():
        from app.services.truth_store import get_skills
        raw = get_skills()
        if isinstance(raw, dict):
            return {"categories": raw.get("categories") or {}, "items": raw.get("items") or []}
        return {"categories": {}, "items": raw if isinstance(raw, list) else []}
    row = db.query(UserSkills).filter(UserSkills.user_id == user_id).first()
    if not row:
        row = UserSkills(user_id=user_id, categories={}, items=[])
        db.add(row)
        db.commit()
        db.refresh(row)
    return _row_to_skills(row)


@router.put("")
def update_skills(
    request: Request,
    data: SkillsUpdate,
    user_id: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    verify_csrf(request)
    if not get_settings().use_postgres():
        from fastapi import HTTPException
        raise HTTPException(status_code=501, detail="Skills are file-based when not using Postgres. Set DATABASE_URL to use DB.")
    row = db.query(UserSkills).filter(UserSkills.user_id == user_id).first()
    if not row:
        row = UserSkills(user_id=user_id, categories=data.categories or {}, items=data.items or [])
        db.add(row)
    else:
        if data.categories is not None:
            row.categories = data.categories
        if data.items is not None:
            row.items = data.items
        db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_skills(row)
