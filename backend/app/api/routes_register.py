"""Registration with invite-code validation; creates user via Supabase Admin API."""
import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import InviteCode
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    invite_code: str


class RegisterResponse(BaseModel):
    ok: bool
    detail: str | None = None


def _validate_invite_code(db: Session, code: str) -> InviteCode | None:
    """Return the InviteCode row if valid (active, not expired, has remaining uses)."""
    row = db.query(InviteCode).filter(InviteCode.code == code.strip()).first()
    if not row:
        return None
    if not row.is_active:
        return None
    if row.expires_at:
        exp = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > exp:
            return None
    if row.used_count >= row.max_uses:
        return None
    return row


@router.post("/register", response_model=RegisterResponse)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user. Requires a valid invite code."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=503,
            detail="Registration is not configured (Supabase not set up)",
        )

    invite = _validate_invite_code(db, data.invite_code)
    if not invite:
        raise HTTPException(status_code=400, detail="Invalid or expired invite code")

    # Create user via Supabase Admin API
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "email": data.email,
        "password": data.password,
        "email_confirm": True,
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        body = e.response.json() if e.response.content else {}
        msg = body.get("msg") or body.get("message") or e.response.text or str(e)
        logger.warning("Supabase create user failed: %s", msg)
        if e.response.status_code == 422:
            raise HTTPException(status_code=400, detail=msg or "Invalid email or password")
        raise HTTPException(status_code=502, detail=msg or "Could not create account")
    except httpx.RequestError as e:
        logger.exception("Supabase request error")
        raise HTTPException(status_code=502, detail="Registration service unavailable")

    # Increment invite code usage
    invite.used_count += 1
    db.commit()

    return RegisterResponse(ok=True)
