"""Job status change logging and timestamp updates for stats."""
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.db.models import Job, JobStatusEvent

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Map application status strings to the job timestamp field to set when entering that status.
STATUS_TO_TIMESTAMP = {
    "Submitted - Pending Response": "applied_at",
    "Interviewing": "interview_at",
    "Rejected": "rejected_at",
    "Offer Extended - In Progress": "offered_at",
    "Rescinded Application (Self) / Decided not a good fit": "withdrawn_at",
    "N/A": None,  # no timestamp
}


def log_status_change(
    db: "Session",
    user_id: str,
    job_id: int,
    old_status: str | None,
    new_status: str,
    notes: str | None = None,
) -> None:
    """Insert a row into job_status_events for timeline and analytics."""
    event = JobStatusEvent(
        user_id=user_id,
        job_id=job_id,
        old_status=old_status,
        new_status=new_status,
        notes=notes,
    )
    db.add(event)


def update_timestamp_fields(db: "Session", job: Job, new_status: str) -> None:
    """Set the appropriate timestamp on the job when status changes. Only sets if the
    corresponding field is currently null (first time entering that status).
    """
    field_name = STATUS_TO_TIMESTAMP.get(new_status)
    if not field_name:
        return
    now = datetime.now(timezone.utc)
    if hasattr(job, field_name) and getattr(job, field_name) is None:
        setattr(job, field_name, now)
        db.add(job)
