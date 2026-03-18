"""Application stats: summary, funnel, timeline, sources, timing, insights."""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.models import Job

if TYPE_CHECKING:
    pass


def _user_jobs_query(db: Session, user_id: str):
    return db.query(Job).filter(or_(Job.user_id == user_id, Job.user_id.is_(None)))


def get_summary(user_id: str, db: Session) -> dict[str, Any]:
    """Aggregate counts for summary cards: total saved, applied, interviewing, rejected, offers, withdrawn, active."""
    base = _user_jobs_query(db, user_id)
    total_saved = base.count()

    applied_status = "Submitted - Pending Response"
    interviewing_status = "Interviewing"
    rejected_status = "Rejected"
    offer_status = "Offer Extended - In Progress"

    total_applied = base.filter(Job.status == applied_status).count()
    total_interviewing = base.filter(Job.status == interviewing_status).count()
    total_rejected = base.filter(Job.status == rejected_status).count()
    total_offers = base.filter(Job.status == offer_status).count()
    total_withdrawn = base.filter(
        or_(
            Job.status == "Rescinded Application (Self) / Decided not a good fit",
            Job.status == "N/A",
        )
    ).count()

    # Active pipeline: applied or interviewing (not rejected, not offer, not withdrawn)
    active_statuses = (applied_status, interviewing_status, "Sent Follow Up Email", "Re-Applied With Updated Resume")
    active_pipeline = base.filter(Job.status.in_(active_statuses)).count()

    return {
        "total_saved": total_saved,
        "total_applied": total_applied,
        "total_interviewing": total_interviewing,
        "total_rejected": total_rejected,
        "total_offers": total_offers,
        "total_withdrawn": total_withdrawn,
        "active_pipeline": active_pipeline,
    }


def get_funnel(user_id: str, db: Session) -> dict[str, Any]:
    """Counts by status for funnel visualization."""
    rows = (
        _user_jobs_query(db, user_id)
        .with_entities(Job.status, func.count(Job.id).label("count"))
        .group_by(Job.status)
        .all()
    )
    return {"by_status": {r.status: r.count for r in rows}}


def _parse_row_period_to_date(period: Any, period_kind: str) -> date:
    if period_kind == "day":
        if isinstance(period, datetime):
            return period.astimezone(timezone.utc).date() if period.tzinfo else period.date()
        if isinstance(period, date):
            return period
        s = str(period)[:10]
        return date.fromisoformat(s)
    if isinstance(period, datetime):
        return period.date()
    return date.fromisoformat(str(period)[:10])


def get_timeline(user_id: str, db: Session, period: str = "day") -> dict[str, Any]:
    """Time series: jobs created per period. period in ('day', 'week', 'month'). Default day for smoother charts."""
    base = _user_jobs_query(db, user_id).filter(Job.created_at.isnot(None))
    applications: list[Any] = []
    period_kind = period if period in ("day", "week", "month") else "day"

    try:
        if period_kind == "day":
            date_expr = func.date_trunc("day", Job.created_at)
        elif period_kind == "week":
            date_expr = func.date_trunc("week", Job.created_at)
        else:
            date_expr = func.date_trunc("month", Job.created_at)
        applications = (
            base.with_entities(date_expr.label("period"), func.count(Job.id).label("count"))
            .group_by(date_expr)
            .order_by(date_expr)
            .all()
        )
    except Exception:
        if period_kind == "day":
            date_expr = func.strftime("%Y-%m-%d", Job.created_at)
        elif period_kind == "week":
            date_expr = func.strftime("%Y-%W", Job.created_at)
        else:
            date_expr = func.strftime("%Y-%m", Job.created_at)
        applications = (
            base.with_entities(date_expr.label("period"), func.count(Job.id).label("count"))
            .group_by(date_expr)
            .order_by(date_expr)
            .all()
        )

    if not applications:
        return {"period": period_kind, "labels": [], "counts": []}

    if period_kind == "day":
        by_day: dict[date, int] = defaultdict(int)
        for r in applications:
            d = _parse_row_period_to_date(r.period, "day")
            by_day[d] += int(r.count)
        start_d = min(by_day)
        end_d = max(by_day)
        if start_d == end_d:
            start_d = start_d - timedelta(days=5)
            end_d = end_d + timedelta(days=1)
        max_days = 548
        if (end_d - start_d).days > max_days:
            start_d = end_d - timedelta(days=max_days)
        labels: list[str] = []
        counts: list[int] = []
        cur = start_d
        while cur <= end_d:
            labels.append(cur.isoformat())
            counts.append(by_day.get(cur, 0))
            cur += timedelta(days=1)
        return {"period": "day", "labels": labels, "counts": counts}

    if period_kind == "week":
        labels = [r.period.isoformat()[:10] if hasattr(r.period, "isoformat") else str(r.period) for r in applications]
    else:
        labels = [r.period.isoformat()[:7] if hasattr(r.period, "isoformat") else str(r.period)[:7] for r in applications]
    return {
        "period": period_kind,
        "labels": labels,
        "counts": [r.count for r in applications],
    }


def get_sources(user_id: str, db: Session) -> dict[str, Any]:
    """Breakdown by source_platform. Null/empty grouped as 'Other' or 'Not set'."""
    rows = (
        _user_jobs_query(db, user_id)
        .with_entities(
            func.coalesce(Job.source_platform, "").label("platform"),
            func.count(Job.id).label("count"),
        )
        .group_by(func.coalesce(Job.source_platform, ""))
        .all()
    )
    by_source = {}
    for r in rows:
        key = r.platform.strip() if r.platform else "Not set"
        by_source[key] = r.count
    return {"by_source": by_source}


def get_timing_metrics(user_id: str, db: Session) -> dict[str, Any]:
    """Average days between key events using job timestamps (applied_at -> first_response, etc.)."""
    base = _user_jobs_query(db, user_id)
    # Postgres: EXTRACT(EPOCH FROM (a - b))/86400; SQLite: julianday(a) - julianday(b)
    try:
        days_expr = func.extract("epoch", Job.first_response_at - Job.applied_at) / 86400
        avg_days = base.filter(
            Job.applied_at.isnot(None),
            Job.first_response_at.isnot(None),
        ).with_entities(func.avg(days_expr)).scalar()
        days_expr2 = func.extract("epoch", Job.interview_at - Job.applied_at) / 86400
        avg_days_ai = base.filter(
            Job.applied_at.isnot(None),
            Job.interview_at.isnot(None),
        ).with_entities(func.avg(days_expr2)).scalar()
    except Exception:
        days_expr = func.julianday(Job.first_response_at) - func.julianday(Job.applied_at)
        avg_days = base.filter(
            Job.applied_at.isnot(None),
            Job.first_response_at.isnot(None),
        ).with_entities(func.avg(days_expr)).scalar()
        days_expr2 = func.julianday(Job.interview_at) - func.julianday(Job.applied_at)
        avg_days_ai = base.filter(
            Job.applied_at.isnot(None),
            Job.interview_at.isnot(None),
        ).with_entities(func.avg(days_expr2)).scalar()
    return {
        "avg_days_applied_to_first_response": round(float(avg_days), 1) if avg_days is not None else None,
        "avg_days_applied_to_interview": round(float(avg_days_ai), 1) if avg_days_ai is not None else None,
    }


def get_sankey_flow_text(user_id: str, db: Session) -> str:
    """Build SankeyMATIC flow text from funnel/summary for Applications → Interviews → Offers pipeline.
    Format: Source [AMOUNT] Target (one per line). Only includes flows with amount > 0.
    See https://sankeymatic.com/build/ and manual for syntax.
    """
    summary = get_summary(user_id, db)
    total_applied = summary["total_applied"]
    total_interviewing = summary["total_interviewing"]
    total_rejected = summary["total_rejected"]
    total_offers = summary["total_offers"]
    # No Answer = applied but not yet interviewed or rejected
    no_answer = max(0, total_applied - total_interviewing - total_rejected)
    no_offer = max(0, total_interviewing - total_offers)

    lines: list[str] = []
    if total_applied > 0:
        if total_interviewing > 0:
            lines.append(f"Applications [{total_interviewing}] Interviews")
        if total_rejected > 0:
            lines.append(f"Applications [{total_rejected}] Rejected")
        if no_answer > 0:
            lines.append(f"Applications [{no_answer}] No Answer")
    if total_interviewing > 0:
        if total_offers > 0:
            lines.append(f"Interviews [{total_offers}] Offers")
        if no_offer > 0:
            lines.append(f"Interviews [{no_offer}] No Offer")
    if total_offers > 0:
        lines.append(f"Offers [{total_offers}] Outcome")

    if not lines:
        return "Applications [0] Interviews\n// Add job applications and update their status to see your pipeline here."
    return "\n".join(lines)


def get_insights(user_id: str, db: Session) -> list[str]:
    """Rule-based insight strings."""
    insights = []
    summary = get_summary(user_id, db)
    base = _user_jobs_query(db, user_id)

    # Stale applications: applied for > 14 days with no status change
    applied_status = "Submitted - Pending Response"
    stale = base.filter(Job.status == applied_status)
    if hasattr(Job, "applied_at"):
        from datetime import datetime, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=14)
        stale = stale.filter(Job.applied_at.isnot(None), Job.applied_at < cutoff)
    stale_count = stale.count()
    if stale_count > 0:
        insights.append(f"You have {stale_count} application(s) in \"Submitted\" status for more than 14 days. Consider following up.")

    # Response rate (if we have enough data)
    total_applied = summary["total_applied"]
    total_interviewing = summary["total_interviewing"]
    total_rejected = summary["total_rejected"]
    responded = total_interviewing + total_rejected
    if total_applied >= 5 and responded > 0:
        rate = round(100 * responded / total_applied)
        insights.append(f"About {rate}% of your applications have received a response (interview or rejection).")

    # LinkedIn vs other sources (if source_platform is used)
    sources = get_sources(user_id, db).get("by_source") or {}
    linkedin = sources.get("linkedin") or sources.get("LinkedIn") or 0
    other_total = sum(v for k, v in sources.items() if k.lower() not in ("linkedin", "not set"))
    if linkedin >= 3 and other_total >= 3:
        insights.append("Consider comparing response rates by source in the Stats dashboard (e.g. LinkedIn vs Indeed).")

    # Interview prep suggestion
    if summary["total_interviewing"] > 0:
        insights.append("You have jobs in Interviewing status. Use Interview Prep on each job page to prepare.")

    return insights
