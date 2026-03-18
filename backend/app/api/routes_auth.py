"""Auth routes: me, demo login, legacy login/logout."""
import hashlib
import hmac
import logging
import secrets
import time
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_COOKIE = "jobkit_session"
CSRF_COOKIE = "jobkit_csrf"


class MeResponse(BaseModel):
    user_id: str
    email: str | None = None
    is_demo: bool = False


@router.get("/me", response_model=MeResponse)
def me(user_id: str = Depends(get_current_user)):
    """Return current user info. Works for both JWT and legacy session auth."""
    settings = get_settings()
    is_demo = bool(settings.demo_user_id and user_id == settings.demo_user_id)
    return MeResponse(user_id=user_id, is_demo=is_demo)


@router.post("/demo-login")
def demo_login():
    """Sign in as the read-only demo user. Returns Supabase session tokens."""
    settings = get_settings()
    if not settings.demo_user_email or not settings.demo_user_password:
        raise HTTPException(status_code=404, detail="Demo login not configured")
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": settings.supabase_anon_key,
        "Content-Type": "application/json",
    }
    payload = {
        "email": settings.demo_user_email,
        "password": settings.demo_user_password,
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.warning("Demo login failed: %s", e.response.text)
        raise HTTPException(status_code=502, detail="Demo login failed")
    except httpx.RequestError:
        logger.exception("Demo login request error")
        raise HTTPException(status_code=502, detail="Auth service unavailable")

    return resp.json()


# ---------------------------------------------------------------------------
# Legacy login/logout -- kept so the old frontend keeps working until
# fully migrated to Supabase Auth. Will be removed.
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str
    password: str


def _cookie_domain() -> str | None:
    settings = get_settings()
    try:
        parsed = urlparse(settings.app_url)
        return parsed.hostname or None
    except Exception:
        return None


@router.post("/login")
def login(data: LoginRequest, response: Response):
    settings = get_settings()
    if data.username != settings.admin_username or data.password != settings.admin_password:
        return {"ok": False, "detail": "Invalid username or password"}
    raw = f"{data.username}:{int(time.time())}"
    sig = hmac.new(settings.session_secret.encode(), raw.encode(), hashlib.sha256).hexdigest()[:16]
    session_val = f"{raw}:{sig}"
    csrf_val = secrets.token_urlsafe(32)
    secure = settings.app_env == "prod"
    domain = _cookie_domain()
    common = {"max_age": 7 * 86400, "samesite": "lax", "secure": secure, "path": "/"}
    if domain:
        common["domain"] = domain
    response.set_cookie(key=SESSION_COOKIE, value=session_val, httponly=True, **common)
    response.set_cookie(key=CSRF_COOKIE, value=csrf_val, httponly=False, **common)
    return {"ok": True, "username": data.username}


@router.post("/logout")
def logout(response: Response):
    domain = _cookie_domain()
    response.delete_cookie(SESSION_COOKIE, path="/", **({"domain": domain} if domain else {}))
    response.delete_cookie(CSRF_COOKIE, path="/", **({"domain": domain} if domain else {}))
    return {"ok": True}


class CsrfResponse(BaseModel):
    token: str


@router.get("/csrf", response_model=CsrfResponse)
def csrf(response: Response, user_id: str = Depends(get_current_user)):
    """Issue a CSRF token -- still needed for legacy cookie auth path."""
    token = secrets.token_urlsafe(32)
    secure = get_settings().app_env == "prod"
    domain = _cookie_domain()
    kwargs = {"max_age": 7 * 86400, "httponly": False, "samesite": "lax", "secure": secure, "path": "/"}
    if domain:
        kwargs["domain"] = domain
    response.set_cookie(key=CSRF_COOKIE, value=token, **kwargs)
    return CsrfResponse(token=token)
