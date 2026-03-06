"""Google OAuth."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.db.models import GoogleToken
from app.services.google_auth import auth_url, exchange_code, save_refresh_token

router = APIRouter(prefix="/api/google", tags=["google"])


@router.get("/status")
def google_status(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_user)],
):
    row = db.query(GoogleToken).filter(GoogleToken.provider == "google").first()
    if not row:
        return {"connected": False, "scopes": []}
    return {"connected": True, "scopes": (row.scopes or "").split(",")}


@router.get("/oauth/start")
def oauth_start(
    _: Annotated[str, Depends(get_current_user)],
):
    url = auth_url()
    return RedirectResponse(url=url)


@router.get("/oauth/callback")
def oauth_callback(
    db: Annotated[Session, Depends(get_db)],
    code: str | None = None,
):
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")
    try:
        creds, refresh = exchange_code(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth failed: {e}") from e
    if not refresh:
        raise HTTPException(status_code=400, detail="No refresh token")
    save_refresh_token(db, refresh)
    settings = get_settings()
    return RedirectResponse(url=settings.app_url.rstrip("/") + "/")
