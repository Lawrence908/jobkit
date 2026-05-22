"""Google OAuth 2.0 flow and token storage."""
import logging

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from sqlalchemy import or_

from app.core.config import get_settings
from app.core.crypto import decrypt_refresh_token, encrypt_refresh_token
from app.db.models import GoogleToken

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_flow():
    settings = get_settings()
    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_oauth_redirect_uri],
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.google_oauth_redirect_uri,
        autogenerate_code_verifier=False,
    )


def auth_url() -> str:
    """Legacy: auth URL without state."""
    flow = get_flow()
    url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    return url


def auth_url_with_state(state: str) -> str:
    """Auth URL with state parameter for user identification in callback."""
    flow = get_flow()
    url, _ = flow.authorization_url(access_type="offline", prompt="consent", state=state)
    return url


def exchange_code(code: str) -> tuple[Credentials, str]:
    flow = get_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    refresh = creds.refresh_token or ""
    return creds, refresh


def save_refresh_token(db, refresh_token: str, user_id: str | None = None) -> None:
    settings = get_settings()
    encrypted = encrypt_refresh_token(refresh_token, settings.google_token_encryption_key)
    if user_id:
        existing = db.query(GoogleToken).filter(
            GoogleToken.provider == "google",
            GoogleToken.user_id == user_id,
        ).first()
    else:
        existing = db.query(GoogleToken).filter(GoogleToken.provider == "google").first()
    if existing:
        existing.encrypted_refresh_token = encrypted
        existing.scopes = ",".join(SCOPES)
        if user_id:
            existing.user_id = user_id
        db.add(existing)
    else:
        db.add(GoogleToken(
            user_id=user_id,
            provider="google",
            encrypted_refresh_token=encrypted,
            scopes=",".join(SCOPES),
        ))
    db.commit()


def get_credentials(db, user_id: str | None = None):
    """Return credentials for the given user. When user_id is set, only that user's token is used (no global fallback)."""
    if user_id:
        row = db.query(GoogleToken).filter(
            GoogleToken.provider == "google",
            GoogleToken.user_id == user_id,
        ).first()
    else:
        row = db.query(GoogleToken).filter(GoogleToken.provider == "google").first()
    if not row:
        return None
    settings = get_settings()
    refresh = decrypt_refresh_token(row.encrypted_refresh_token, settings.google_token_encryption_key)
    if not refresh:
        return None
    return Credentials(
        token=None,
        refresh_token=refresh,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        scopes=SCOPES,
    )


def clear_token(db, user_id: str) -> None:
    """Remove a user's stored Google token (e.g. after it is revoked/expired)."""
    db.query(GoogleToken).filter(
        GoogleToken.provider == "google",
        GoogleToken.user_id == user_id,
    ).delete()
    db.commit()


def verify_credentials(db, user_id: str):
    """Return live credentials if the user's refresh token still works, else None.

    Performs a lightweight token refresh against Google. If the refresh token has
    been revoked or expired (invalid_grant), the stale row is deleted so the app
    stops reporting a false "connected" state. Transient/transport errors are
    treated as still-connected so a network blip does not drop a valid connection.
    """
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request

    creds = get_credentials(db, user_id=user_id)
    if creds is None:
        return None
    try:
        creds.refresh(Request())
        return creds
    except RefreshError as e:
        if "invalid_grant" in str(e).lower():
            clear_token(db, user_id)
            return None
        logger.warning("Google token refresh error for user %s: %s", user_id, e)
        return creds
    except Exception as e:
        logger.warning("Google token verification failed for user %s: %s", user_id, e)
        return creds
