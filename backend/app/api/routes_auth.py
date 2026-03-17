"""Auth routes: me, legacy login/logout (kept for backward compat during migration)."""
import hashlib
import hmac
import secrets
import time
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_COOKIE = "jobkit_session"
CSRF_COOKIE = "jobkit_csrf"


class MeResponse(BaseModel):
    user_id: str
    email: str | None = None


@router.get("/me", response_model=MeResponse)
def me(user_id: str = Depends(get_current_user)):
    """Return current user info. Works for both JWT and legacy session auth."""
    return MeResponse(user_id=user_id)


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
