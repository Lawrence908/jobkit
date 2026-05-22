"""Google OAuth and sheet data."""
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.db.models import GoogleToken
from app.services.google_auth import auth_url_with_state, exchange_code, get_credentials, save_refresh_token, verify_credentials
from app.services.google_sheets import get_all_sheet_data

router = APIRouter(prefix="/api/google", tags=["google"])

# Temporary in-memory map: state -> user_id (for OAuth callback)
_pending_oauth: dict[str, str] = {}


@router.get("/status")
def google_status(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    """Connected only when this user has their own Google token that still refreshes.

    Verifies the refresh token with Google so an expired or revoked token reports
    disconnected (and is cleared) instead of a false "connected".
    """
    row = db.query(GoogleToken).filter(
        GoogleToken.provider == "google",
        GoogleToken.user_id == user_id,
    ).first()
    if not row:
        return {"connected": False, "scopes": []}
    if verify_credentials(db, user_id) is None:
        return {"connected": False, "scopes": []}
    return {"connected": True, "scopes": (row.scopes or "").split(",")}


@router.get("/oauth/start")
def oauth_start(
    user_id: Annotated[str, Depends(get_current_user)],
):
    """Return the Google OAuth URL. Frontend should navigate to it.

    For JWT auth: returns JSON with auth_url.
    For legacy cookie auth: redirects directly (backward compat).
    """
    state = secrets.token_urlsafe(32)
    _pending_oauth[state] = user_id
    url = auth_url_with_state(state)
    return {"auth_url": url}


@router.get("/oauth/callback")
def oauth_callback(
    db: Annotated[Session, Depends(get_db)],
    code: str | None = None,
    state: str | None = None,
):
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")
    user_id = _pending_oauth.pop(state, None) if state else None
    try:
        creds, refresh = exchange_code(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth failed: {e}") from e
    if not refresh:
        raise HTTPException(status_code=400, detail="No refresh token")
    save_refresh_token(db, refresh, user_id=user_id)
    settings = get_settings()
    return RedirectResponse(url=settings.app_url.rstrip("/") + "/")


@router.get("/sheet")
def get_sheet_data(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    from app.services.profile_store import get_profile

    row = db.query(GoogleToken).filter(
        GoogleToken.provider == "google",
        GoogleToken.user_id == user_id,
    ).first()
    if not row:
        raise HTTPException(status_code=403, detail="Google not connected")
    creds = get_credentials(db, user_id=user_id)
    if not creds:
        raise HTTPException(status_code=403, detail="Google credentials unavailable")

    profile = get_profile(user_id, db)
    settings = get_settings()
    spreadsheet_id = (profile.get("google_sheets_spreadsheet_id") or "").strip() or settings.google_sheets_spreadsheet_id
    sheet_name = (profile.get("google_sheets_tab_name") or "").strip() or settings.google_sheets_tab_name
    if not spreadsheet_id or not sheet_name:
        raise HTTPException(
            status_code=400,
            detail="Google Sheet not configured. Set your spreadsheet and tab in Profile or Connections.",
        )
    service = build("sheets", "v4", credentials=creds)
    headers, rows = get_all_sheet_data(service, spreadsheet_id, sheet_name)
    spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    return {
        "spreadsheet_url": spreadsheet_url,
        "sheet_name": sheet_name,
        "headers": headers,
        "rows": rows,
    }
