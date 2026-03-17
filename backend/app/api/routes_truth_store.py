"""Truth store status and reload."""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.services.truth_store import get_loaded_at, get_projects, load_truth_store

router = APIRouter(prefix="/api/truth-store", tags=["truth-store"])


@router.get("/status")
def truth_store_status(
    user_id: Annotated[str, Depends(get_current_user)],
):
    loaded_at = get_loaded_at()
    projects = get_projects()
    return {
        "loaded": loaded_at is not None,
        "loaded_at": loaded_at,
        "project_count": len(projects),
    }


@router.post("/reload")
def truth_store_reload(
    user_id: Annotated[str, Depends(get_current_user)],
):
    load_truth_store()
    loaded_at = get_loaded_at()
    projects = get_projects()
    return {
        "ok": True,
        "loaded_at": loaded_at,
        "project_count": len(projects),
    }
