"""Application stats API: summary, funnel, timeline, sources, insights."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.services.application_stats_service import (
    get_funnel,
    get_insights,
    get_sankey_flow_text,
    get_sources,
    get_summary,
    get_timeline,
    get_timing_metrics,
)

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/summary")
def stats_summary(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    return get_summary(user_id, db)


@router.get("/funnel")
def stats_funnel(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    return get_funnel(user_id, db)


@router.get("/timeline")
def stats_timeline(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
    period: Annotated[str, Query(description="day (default), week, or month")] = "day",
):
    return get_timeline(user_id, db, period=period)


@router.get("/sources")
def stats_sources(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    return get_sources(user_id, db)


@router.get("/timing")
def stats_timing(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    return get_timing_metrics(user_id, db)


@router.get("/insights")
def stats_insights(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    return {"insights": get_insights(user_id, db)}


SANKEYMATIC_BUILD_URL = "https://sankeymatic.com/build/"


@router.get("/sankey")
def stats_sankey(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    """Return SankeyMATIC flow text and build URL so the frontend can open SankeyMATIC with user data."""
    flow_text = get_sankey_flow_text(user_id, db)
    return {
        "flow_text": flow_text,
        "sankeymatic_build_url": SANKEYMATIC_BUILD_URL,
    }
