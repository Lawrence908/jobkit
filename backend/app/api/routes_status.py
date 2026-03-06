"""Status and health routes."""
from fastapi import APIRouter

router = APIRouter(tags=["status"])


@router.get("/api/health")
def health():
    return {"status": "ok"}
