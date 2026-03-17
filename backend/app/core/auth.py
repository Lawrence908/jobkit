"""Auth: Supabase JWT validation with legacy session cookie fallback."""
import hashlib
import hmac
import logging
import time
from typing import Annotated

import jwt
from jwt import PyJWKClient
from fastapi import Cookie, Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

SESSION_COOKIE = "jobkit_session"
SESSION_MAX_AGE = 86400 * 7

# Algorithms Supabase may use: HS256 (legacy), RS256/ES256 (JWKS)
_HS256_OPTS = {"algorithms": ["HS256"], "audience": "authenticated"}
_ASYMMETRIC_ALGS = ["RS256", "ES256"]


def _decode_supabase_jwt(token: str, settings: Settings) -> dict:
    """Decode and validate a Supabase access token. Returns the payload.

    Tries HS256 with JWT secret first (legacy). If the token uses RS256/ES256
    (Supabase signing keys), verifies via the project JWKS endpoint.
    """
    header = jwt.get_unverified_header(token)
    alg = header.get("alg", "HS256")

    if alg == "HS256" and settings.supabase_jwt_secret:
        try:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                **_HS256_OPTS,
            )
        except jwt.InvalidAudienceError:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )

    if alg in _ASYMMETRIC_ALGS and settings.supabase_url:
        jwks_uri = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        jwks_client = PyJWKClient(jwks_uri)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        try:
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=_ASYMMETRIC_ALGS,
                audience="authenticated",
            )
        except jwt.InvalidAudienceError:
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=_ASYMMETRIC_ALGS,
                options={"verify_aud": False},
            )

    raise jwt.InvalidTokenError(f"Unsupported or missing alg: {alg}")


def get_current_user(
    request: Request,
    jobkit_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> str:
    """Dependency: return user_id (UUID string) from Supabase JWT, or fall back to legacy session.

    Priority:
    1. Authorization: Bearer <supabase_jwt> -> user_id from JWT sub claim
    2. Legacy session cookie -> admin_username (for backward compat during migration)
    """
    settings = get_settings()

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if settings.supabase_jwt_secret:
            try:
                payload = _decode_supabase_jwt(token, settings)
                user_id = payload.get("sub")
                if not user_id:
                    raise HTTPException(status_code=401, detail="Invalid token: no sub")
                return user_id
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=401, detail="Token expired")
            except jwt.InvalidTokenError as e:
                logger.warning("JWT validation failed: %s", e)
                raise HTTPException(status_code=401, detail="Invalid token")

    if jobkit_session:
        username = _verify_legacy_session(jobkit_session, settings)
        if username:
            return username

    raise HTTPException(status_code=401, detail="Not authenticated")


def get_optional_user(
    request: Request,
    jobkit_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> str | None:
    """Dependency: return user_id if authenticated, else None."""
    try:
        return get_current_user(request, jobkit_session)
    except HTTPException:
        return None


# ---------------------------------------------------------------------------
# Legacy session support (will be removed after full migration to Supabase Auth)
# ---------------------------------------------------------------------------

def _verify_legacy_session(payload: str, settings: Settings) -> str | None:
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


def verify_csrf(request: Request) -> None:
    """CSRF check -- now a no-op for JWT-authenticated requests.

    JWT auth is immune to CSRF since the token is sent via Authorization header.
    Kept as a callable for backward compat; route handlers that call it won't break.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return
    # Legacy cookie path: check CSRF header vs cookie
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    header_token = request.headers.get("X-CSRF-Token")
    if not header_token:
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    csrf_cookie = request.cookies.get("jobkit_csrf")
    if csrf_cookie and hmac.compare_digest(csrf_cookie, header_token):
        return
    raise HTTPException(status_code=403, detail="Invalid CSRF token")
