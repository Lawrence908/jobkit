"""Single-user auth: session cookie, rate limiting, CSRF."""
import hashlib
import hmac
import secrets
import time
from collections import deque
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from app.core.config import Settings, get_settings
SESSION_COOKIE = "jobkit_session"
CSRF_COOKIE = "jobkit_csrf"
SESSION_MAX_AGE = 86400 * 7  # 7 days
LOGIN_RATE_LIMIT = 5
LOGIN_RATE_WINDOW = 60  # seconds
CSRF_TOKEN_TTL = 300  # 5 minutes

# In-memory: (timestamp,) of recent failed logins
_failed_logins: deque[float] = deque(maxlen=100)
# username -> (token, expiry_ts) for CSRF tokens issued via GET /api/auth/csrf (works when cookie is not forwarded by proxy)
_csrf_tokens: dict[str, tuple[str, float]] = {}


def _session_payload(username: str) -> str:
    settings = get_settings()
    raw = f"{username}:{int(time.time())}"
    sig = hmac.new(
        settings.session_secret.encode("utf-8"),
        raw.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:16]
    return f"{raw}:{sig}"


def verify_session(payload: str) -> str | None:
    """Verify session payload; return username or None."""
    settings = get_settings()
    parts = payload.split(":")
    if len(parts) != 3:
        return None
    username, ts_str, sig = parts
    try:
        ts = int(ts_str)
        if time.time() - ts > SESSION_MAX_AGE:
            return None
    except ValueError:
        return None
    raw = f"{username}:{ts_str}"
    expected = hmac.new(
        settings.session_secret.encode("utf-8"),
        raw.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:16]
    if not hmac.compare_digest(expected, sig):
        return None
    if username != settings.admin_username:
        return None
    return username


def create_session_cookie(username: str) -> tuple[str, str]:
    """Return (session_cookie_value, csrf_token)."""
    payload = _session_payload(username)
    csrf = secrets.token_urlsafe(32)
    return payload, csrf


def create_csrf_token() -> str:
    """Return a new CSRF token (for refresh endpoint)."""
    return secrets.token_urlsafe(32)


def store_csrf_token(username: str, token: str) -> None:
    """Store a CSRF token for this user (from GET /api/auth/csrf). Valid for CSRF_TOKEN_TTL."""
    _csrf_tokens[username] = (token, time.time() + CSRF_TOKEN_TTL)


def _check_stored_csrf_token(username: str | None, token: str | None) -> bool:
    """True if username and token match a valid stored token."""
    if not username or not token:
        return False
    entry = _csrf_tokens.get(username)
    if not entry:
        return False
    stored_token, expiry = entry
    if time.time() > expiry:
        del _csrf_tokens[username]
        return False
    return hmac.compare_digest(stored_token, token)


def check_login_rate_limit() -> None:
    """Raise 429 if too many failed logins in the window."""
    now = time.time()
    while _failed_logins and _failed_logins[0] < now - LOGIN_RATE_WINDOW:
        _failed_logins.popleft()
    if len(_failed_logins) >= LOGIN_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )


def record_failed_login() -> None:
    _failed_logins.append(time.time())


def get_current_user(
    request: Request,
    jobkit_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,
) -> str:
    """Dependency: require valid session; return username."""
    if not jobkit_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    username = verify_session(jobkit_session)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    return username


def get_optional_user(
    jobkit_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> str | None:
    """Dependency: return username if valid session, else None."""
    if not jobkit_session:
        return None
    return verify_session(jobkit_session)


def verify_csrf(request: Request) -> None:
    """Validate CSRF: X-CSRF-Token header must match cookie jobkit_csrf, or a token we issued via GET /api/auth/csrf for this session (fallback when proxy does not forward cookies)."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    header_token = request.headers.get("X-CSRF-Token")
    if not header_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )
    jobkit_csrf = request.cookies.get(CSRF_COOKIE)
    if jobkit_csrf and hmac.compare_digest(jobkit_csrf, header_token):
        return
    jobkit_session = request.cookies.get(SESSION_COOKIE)
    username = verify_session(jobkit_session) if jobkit_session else None
    if _check_stored_csrf_token(username, header_token):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid CSRF token",
    )
