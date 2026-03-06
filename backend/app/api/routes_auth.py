"""Auth routes: login, logout, me."""
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from app.core.auth import (
    SESSION_COOKIE,
    CSRF_COOKIE,
    check_login_rate_limit,
    create_session_cookie,
    create_csrf_token,
    get_current_user,
    record_failed_login,
    store_csrf_token,
    verify_csrf,
)
from app.core.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class MeResponse(BaseModel):
    username: str


def _cookie_domain() -> str | None:
    """Cookie domain from APP_URL so the browser sends cookies when using the public host (e.g. behind Caddy)."""
    settings = get_settings()
    try:
        parsed = urlparse(settings.app_url)
        return parsed.hostname or None
    except Exception:
        return None


def _set_auth_cookies(response: Response, session_value: str, csrf_value: str) -> None:
    settings = get_settings()
    secure = settings.app_env == "prod"
    domain = _cookie_domain()
    common = {"max_age": 7 * 86400, "samesite": "lax", "secure": secure, "path": "/"}
    if domain:
        common["domain"] = domain
    response.set_cookie(key=SESSION_COOKIE, value=session_value, httponly=True, **common)
    response.set_cookie(key=CSRF_COOKIE, value=csrf_value, httponly=False, **common)


def _set_csrf_cookie_only(response: Response, csrf_value: str) -> None:
    settings = get_settings()
    secure = settings.app_env == "prod"
    domain = _cookie_domain()
    kwargs = {
        "max_age": 7 * 86400,
        "httponly": False,
        "samesite": "lax",
        "secure": secure,
        "path": "/",
    }
    if domain:
        kwargs["domain"] = domain
    response.set_cookie(key=CSRF_COOKIE, value=csrf_value, **kwargs)


@router.post("/login")
def login(data: LoginRequest, response: Response):
    check_login_rate_limit()
    settings = get_settings()
    if data.username != settings.admin_username or data.password != settings.admin_password:
        record_failed_login()
        return {"ok": False, "detail": "Invalid username or password"}
    session_val, csrf_val = create_session_cookie(data.username)
    _set_auth_cookies(response, session_val, csrf_val)
    return {"ok": True, "username": data.username}


@router.post("/logout")
def logout(response: Response):
    domain = _cookie_domain()
    response.delete_cookie(SESSION_COOKIE, path="/", **({"domain": domain} if domain else {}))
    response.delete_cookie(CSRF_COOKIE, path="/", **({"domain": domain} if domain else {}))
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(username: str = Depends(get_current_user)):
    return MeResponse(username=username)


class CsrfResponse(BaseModel):
    token: str


@router.get("/csrf", response_model=CsrfResponse)
def csrf(response: Response, username: str = Depends(get_current_user)):
    """Issue a fresh CSRF token and set the cookie. Also store server-side so POSTs succeed when proxy does not forward the cookie."""
    token = create_csrf_token()
    store_csrf_token(username, token)
    _set_csrf_cookie_only(response, token)
    return CsrfResponse(token=token)
