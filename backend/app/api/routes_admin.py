"""Admin routes: invite code management. Requires admin (legacy admin_username or ADMIN_USER_ID)."""
import secrets
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.db.models import InviteCode
from app.db.session import get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin(user_id: Annotated[str, Depends(get_current_user)]) -> str:
    """Dependency: require current user to be admin (legacy username or ADMIN_USER_ID)."""
    settings = get_settings()
    if user_id == settings.admin_username:
        return user_id
    if settings.admin_user_id and user_id == settings.admin_user_id:
        return user_id
    raise HTTPException(status_code=403, detail="Admin only")


@router.get("/check", response_model=dict)
def admin_check(_admin: str = Depends(require_admin)):
    """Return { "admin": true } if the current user is an admin. Used by frontend to show/hide Admin UI."""
    return {"admin": True}


# ---------------------------------------------------------------------------
# Invite codes
# ---------------------------------------------------------------------------

class InviteCodeCreate(BaseModel):
    code: str | None = None  # auto-generate if not provided
    label: str = ""
    max_uses: int = 1
    expires_at: datetime | None = None


class InviteCodeUpdate(BaseModel):
    label: str | None = None
    max_uses: int | None = None
    expires_at: datetime | None = None
    is_active: bool | None = None


class InviteCodeOut(BaseModel):
    id: int
    code: str
    label: str
    max_uses: int
    used_count: int
    created_by: str | None
    expires_at: datetime | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


def _make_code() -> str:
    return secrets.token_urlsafe(12).replace("-", "")[:16]


@router.post("/invite-codes", response_model=InviteCodeOut)
def create_invite_code(
    data: InviteCodeCreate,
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin),
):
    """Create a new invite code. If `code` is omitted, one is generated."""
    code = (data.code or _make_code()).strip()
    if not code:
        code = _make_code()
    existing = db.query(InviteCode).filter(InviteCode.code == code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Invite code already exists")
    row = InviteCode(
        code=code,
        label=data.label or "",
        max_uses=data.max_uses,
        expires_at=data.expires_at,
        created_by=admin_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/invite-codes", response_model=list[InviteCodeOut])
def list_invite_codes(
    db: Session = Depends(get_db),
    _admin: str = Depends(require_admin),
    active_only: bool = Query(False, description="Only return active codes"),
):
    """List all invite codes with usage stats."""
    q = db.query(InviteCode).order_by(InviteCode.created_at.desc())
    if active_only:
        q = q.filter(InviteCode.is_active.is_(True))
    return list(q.all())


@router.patch("/invite-codes/{code_id}", response_model=InviteCodeOut)
def update_invite_code(
    code_id: int,
    data: InviteCodeUpdate,
    db: Session = Depends(get_db),
    _admin: str = Depends(require_admin),
):
    """Update an invite code (label, max_uses, expires_at, is_active)."""
    row = db.query(InviteCode).filter(InviteCode.id == code_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Invite code not found")
    if data.label is not None:
        row.label = data.label
    if data.max_uses is not None:
        row.max_uses = data.max_uses
    if data.expires_at is not None:
        row.expires_at = data.expires_at
    if data.is_active is not None:
        row.is_active = data.is_active
    db.commit()
    db.refresh(row)
    return row


@router.delete("/invite-codes/{code_id}", status_code=204)
def delete_invite_code(
    code_id: int,
    db: Session = Depends(get_db),
    _admin: str = Depends(require_admin),
):
    """Delete an invite code."""
    row = db.query(InviteCode).filter(InviteCode.id == code_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Invite code not found")
    db.delete(row)
    db.commit()
