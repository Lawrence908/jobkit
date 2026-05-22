"""Exemplar library status and reload.

The library is loaded from disk at startup and refreshed automatically when an exemplar is
promoted. This reload route is for picking up manual edits to the YAML files on disk.
"""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.routes_admin import require_admin
from app.core.auth import get_current_user
from app.services.exemplar_store import get_exemplars, get_loaded_at, load_exemplars

router = APIRouter(prefix="/api/exemplars", tags=["exemplars"])


def _summary() -> dict:
    exemplars = get_exemplars()
    by_type: dict[str, int] = {}
    for e in exemplars:
        dt = e.get("doc_type") or "unknown"
        by_type[dt] = by_type.get(dt, 0) + 1
    return {
        "loaded": get_loaded_at() is not None,
        "loaded_at": get_loaded_at(),
        "count": len(exemplars),
        "by_doc_type": by_type,
    }


@router.get("/status")
def exemplars_status(
    user_id: Annotated[str, Depends(get_current_user)],
):
    return _summary()


@router.post("/reload")
def exemplars_reload(
    _admin: Annotated[str, Depends(require_admin)],
):
    """Re-read exemplars/*.yml from disk (admin only)."""
    load_exemplars()
    return {"ok": True, **_summary()}
