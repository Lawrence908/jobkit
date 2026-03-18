"""Job CRUD and ingestion."""
import logging
import shutil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, verify_csrf
from app.core.config import get_settings
from app.db.session import get_db
from app.db.models import Artifact, Job
from app.services.ingest import ingest_job, job_json_to_markdown, save_job_to_disk, url_to_job_json, paste_only_to_job_json
from app.services import storage as storage_svc
from app.services.extract import extract_keywords, extract_ats_signals
from app.utils.files import job_slug, ensure_safe_relative_path
from app.services.job_status_service import log_status_change, update_timestamp_fields

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)

# Max length for description preview on list/dashboard cards
DESCRIPTION_PREVIEW_LENGTH = 220


def _has_generated_content(job: Job) -> bool:
    """True if this job has generated content (resume.md etc.). Storage-only when Supabase configured; else disk."""
    if storage_svc.use_storage() and job.user_id:
        try:
            return storage_svc.has_generated_content(job.user_id, job.slug)
        except Exception:
            return False
    gen_dir = ensure_safe_relative_path(get_settings().jobkit_jobs_dir, job.slug, "generated")
    return (gen_dir / "resume.md").exists()


# Application Status options (match Google Sheet dropdown)
APPLICATION_STATUS_OPTIONS = [
    "Have Not Applied",
    "Submitted - Pending Response",
    "Rejected",
    "Interviewing",
    "Offer Extended - In Progress",
    "Sent Follow Up Email",
    "Re-Applied With Updated Resume",
    "N/A",
]

# Rejection Reason options (Job page dropdown when updating result)
REJECTION_REASON_OPTIONS = [
    "N/A",
    "Auto-Reject: No Feedback Provided",
    "1st Round Rejection - Feedback Provided",
    "1st Round Rejection - No Feedback Provided",
    "Middle Round Rejection - Feedback Provided",
    "Middle Round Rejection - No Feedback Provided",
    "Final Round Rejection - Feedback Provided",
    "Final Round Rejection - No Feedback Provided",
    'Generic "Not A Good Fit"',
    "Filled - Internal",
    "Eliminated Role",
    "Changed Job Scope",
    "No New Applicants",
    "Applied Too Late",
    "No Response: Sent Email",
    "Post-Interview Follow-Up Email",
    "Ghosted",
    "Job Rec Removed/Deactivated",
    "Offer Extended - Did Not Accept",
    "Rescinded Application (Self) / Decided not a good fit",
    "Not For Me",
]


class CreateJobRequest(BaseModel):
    url: str | None = None
    raw_text: str | None = None
    status: str | None = None  # Application Status; default below


class UpdateJobRequest(BaseModel):
    status: str | None = None
    rejection_reason: str | None = None
    company: str | None = None
    role: str | None = None
    location: str | None = None
    source_platform: str | None = None
    work_arrangement: str | None = None
    raw_body: str | None = None


class UpdateDescriptionRequest(BaseModel):
    raw_body: str


def _user_jobs(db: Session, user_id: str):
    """Query jobs owned by user_id (includes legacy rows with NULL user_id)."""
    return db.query(Job).filter(or_(Job.user_id == user_id, Job.user_id.is_(None)))


def _get_user_job(db: Session, user_id: str, job_id: int) -> Job:
    job = _user_jobs(db, user_id).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _job_to_response(job: Job) -> dict:
    return {
        "id": job.id,
        "url": job.url,
        "company": job.company,
        "role": job.role,
        "location": job.location,
        "status": job.status,
        "rejection_reason": job.rejection_reason,
        "slug": job.slug,
        "keywords": job.keywords_json or [],
        "source": job.source,
        "source_platform": job.source_platform,
        "work_arrangement": job.work_arrangement,
        "applied_at": job.applied_at.isoformat() if job.applied_at else None,
        "first_response_at": job.first_response_at.isoformat() if job.first_response_at else None,
        "interview_at": job.interview_at.isoformat() if job.interview_at else None,
        "rejected_at": job.rejected_at.isoformat() if job.rejected_at else None,
        "offered_at": job.offered_at.isoformat() if job.offered_at else None,
        "withdrawn_at": job.withdrawn_at.isoformat() if job.withdrawn_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_job(
    request: Request,
    data: CreateJobRequest,
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    verify_csrf(request)
    if not data.url and not data.raw_text:
        raise HTTPException(status_code=400, detail="Provide url or raw_text")
    try:
        job_json = ingest_job(data.url, data.raw_text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    slug = job_json["slug"]
    status = (data.status or "Have Not Applied").strip() or "Have Not Applied"
    job = Job(
        user_id=user_id,
        url=job_json.get("url"),
        company=job_json.get("company") or "",
        role=job_json.get("role") or "",
        location=job_json.get("location") or "",
        status=status,
        slug=slug,
        keywords_json=job_json.get("keywords"),
        source=job_json.get("source") or "",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    if storage_svc.use_storage() and user_id:
        job_md = job_json_to_markdown(job_json)
        try:
            storage_svc.upload_job_files(user_id, slug, job_json, job_md)
        except Exception:
            pass  # non-fatal; disk copy already exists
    return _job_to_response(job)


def _job_ids_with_generated(db: Session, job_ids: list[int]) -> set[int]:
    """Job IDs that have at least one generated artifact (resume/cover/notes). One DB query, no Storage."""
    if not job_ids:
        return set()
    rows = (
        db.query(Artifact.job_id)
        .filter(
            Artifact.job_id.in_(job_ids),
            or_(
                Artifact.path.like("%/generated/%"),
                Artifact.type.in_(["resume_md", "cover_letter_md", "notes_md"]),
            ),
        )
        .distinct()
        .all()
    )
    return {r.job_id for r in rows}


@router.get("")
def list_jobs(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    jobs = _user_jobs(db, user_id).order_by(Job.created_at.desc()).all()
    if not jobs:
        return []
    job_ids = [j.id for j in jobs]
    # Artifact counts per job_id
    counts_query = (
        db.query(Artifact.job_id, func.count(Artifact.id).label("count"))
        .filter(Artifact.job_id.in_(job_ids))
        .group_by(Artifact.job_id)
    )
    artifact_counts = {row.job_id: row.count for row in counts_query}
    # One query for "has generated" (no per-job Storage calls)
    jobs_with_generated = _job_ids_with_generated(db, job_ids) if storage_svc.use_storage() else None
    out = []
    for job in jobs:
        resp = _job_to_response(job)
        # List: avoid Storage calls. Use DB-only preview when disk; when Storage, skip job.json for speed.
        if storage_svc.use_storage() and job.user_id:
            resp["description_preview"] = None
        else:
            stats = _description_stats_from_disk(job)
            preview = stats.get("description_preview") or ""
            if len(preview) > DESCRIPTION_PREVIEW_LENGTH:
                preview = preview[:DESCRIPTION_PREVIEW_LENGTH].rstrip() + "…"
            resp["description_preview"] = preview or None
        resp["has_generated_content"] = (
            job.id in jobs_with_generated
            if jobs_with_generated is not None
            else _has_generated_content(job)
        )
        resp["artifact_count"] = artifact_counts.get(job.id, 0)
        out.append(resp)
    return out


@router.get("/options")
def get_job_options(
    user_id: Annotated[str, Depends(get_current_user)],
):
    """Return Application Status and Rejection Reason options for dropdowns."""
    return {
        "application_status": APPLICATION_STATUS_OPTIONS,
        "rejection_reasons": REJECTION_REASON_OPTIONS,
    }


# Tracker table shape (same as SheetData) for non-Google fallback. Must be before /{job_id}.
TRACKER_HEADERS = [
    "Job URL",
    "Company Name",
    "Role",
    "Application Status",
    "Date Submitted",
    "Link to Job Req",
]


@router.get("/tracker")
def get_tracker(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    """Return tracker-shaped data from the jobs table (no spreadsheet_url). Used when Google is not connected."""
    settings = get_settings()
    jobs = _user_jobs(db, user_id).order_by(Job.created_at.desc()).all()
    base_url = settings.app_url.rstrip("/")
    rows: list[list[str]] = []
    for job in jobs:
        date_str = ""
        if job.created_at:
            dt = job.created_at
            date_str = f"{dt.month}/{dt.day}/{dt.year}"
        link_to_job = f"{base_url}/dashboard/jobs/{job.id}" if base_url else f"/dashboard/jobs/{job.id}"
        rows.append([
            job.url or "",
            job.company or "",
            job.role or "",
            job.status or "",
            date_str,
            link_to_job,
        ])
    return {
        "headers": TRACKER_HEADERS,
        "rows": rows,
    }


def _load_job_json(job: Job) -> dict | None:
    """Load job.json from Storage when Supabase configured, else from disk. Returns None if not found."""
    import json
    if storage_svc.use_storage() and job.user_id:
        try:
            return storage_svc.download_job_json(job.user_id, job.slug)
        except Exception:
            return None
    settings = get_settings()
    job_dir = ensure_safe_relative_path(settings.jobkit_jobs_dir, job.slug)
    job_json_path = job_dir / "job.json"
    if not job_json_path.exists():
        return None
    try:
        return json.loads(job_json_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _description_stats_from_raw_body(raw: str) -> dict:
    """Stats for API responses from an in-memory description (avoids stale storage reads)."""
    raw = (raw or "").strip()
    word_count = len(raw.split()) if raw else 0
    preview = (raw[:400] + "…") if len(raw) > 400 else raw
    return {
        "description_word_count": word_count,
        "description_preview": preview or None,
        "raw_body": raw or None,
    }


def _description_stats_from_disk(job: Job) -> dict:
    """Load job.json and return description_word_count and description_preview for UI."""
    job_json = _load_job_json(job)
    if not job_json:
        return {}
    raw = (job_json.get("raw_body") or "").strip()
    return _description_stats_from_raw_body(raw)


def _persist_job_raw_body(job: Job, raw_body: str) -> str:
    """Write raw_body to job.json, refresh keywords, persist to disk and storage. Returns stripped body."""
    raw_body = (raw_body or "").strip()
    job_json = _load_job_json(job)
    if job_json is None:
        job_json = {
            "url": job.url,
            "company": job.company,
            "role": job.role,
            "location": job.location,
            "raw_body": "",
            "keywords": [],
            "ats": {},
            "source": job.source or "",
        }
    settings = get_settings()
    job_dir = ensure_safe_relative_path(settings.jobkit_jobs_dir, job.slug)
    job_dir.mkdir(parents=True, exist_ok=True)
    job_json["raw_body"] = raw_body
    combined = f"{job.role or ''}\n{raw_body}"
    job_json["keywords"] = extract_keywords(combined)
    job_json["ats"] = extract_ats_signals(combined)
    job_md = job_json_to_markdown(job_json)
    save_job_to_disk(job.slug, job_json, job_md)
    if storage_svc.use_storage() and job.user_id:
        try:
            storage_svc.upload_job_files(job.user_id, job.slug, job_json, job_md)
        except Exception:
            logger.exception(
                "upload_job_files failed after description update; disk copy is updated (user_id=%s slug=%s)",
                job.user_id,
                job.slug,
            )
    job.keywords_json = job_json["keywords"]
    return raw_body


@router.get("/{job_id}")
def get_job(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    job = _get_user_job(db, user_id, job_id)
    out = _job_to_response(job)
    out.update(_description_stats_from_disk(job))
    return out


@router.post("/{job_id}/update-description")
def update_job_description(
    job_id: int,
    request: Request,
    data: UpdateDescriptionRequest,
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    verify_csrf(request)
    job = _get_user_job(db, user_id, job_id)
    saved = _persist_job_raw_body(job, data.raw_body)
    db.commit()
    db.refresh(job)
    out = _job_to_response(job)
    # Echo saved text — re-reading storage can return stale data if upload failed or is eventually consistent
    out.update(_description_stats_from_raw_body(saved))
    return out


def _sync_job_to_sheet_if_configured(job: Job, db: Session) -> None:
    """Sync job to Google Sheet only when the job owner has Google connected and has set a sheet in their profile."""
    if not job.user_id:
        return
    from app.db.models import Artifact
    from app.services.google_auth import get_credentials
    from app.services.google_sheets import sync_job_to_sheet
    from app.api.routes_generate import _build_sheet_column_map
    from app.services.profile_store import get_profile

    profile = get_profile(job.user_id, db)
    spreadsheet_id = (profile.get("google_sheets_spreadsheet_id") or "").strip()
    sheet_name = (profile.get("google_sheets_tab_name") or "").strip()
    if not spreadsheet_id or not sheet_name:
        return
    url_column = (profile.get("google_sheets_url_column") or "").strip() or "Job URL"

    creds = get_credentials(db, user_id=job.user_id)
    if not creds:
        return
    resume_link = cover_link = notes_link = ""
    for art in db.query(Artifact).filter(Artifact.job_id == job.id):
        if art.drive_link:
            if art.type == "resume_pdf":
                resume_link = art.drive_link
            elif art.type == "resume_md" and not resume_link:
                resume_link = art.drive_link
            elif art.type == "cover_letter_pdf":
                cover_link = art.drive_link
            elif art.type == "cover_letter_md" and not cover_link:
                cover_link = art.drive_link
            elif art.type == "notes_md":
                notes_link = art.drive_link
    from googleapiclient.discovery import build
    service = build("sheets", "v4", credentials=creds)
    settings = get_settings()
    column_map = _build_sheet_column_map(settings)
    try:
        sync_job_to_sheet(
            service,
            spreadsheet_id,
            sheet_name,
            url_column,
            job,
            resume_link,
            cover_link,
            notes_link,
            column_map,
        )
    except Exception:
        pass


def _remove_job_from_sheet_if_configured(job: Job, db: Session) -> None:
    """Delete this job's row from the user's Google Sheet so the sheet mirrors the app."""
    if not job.user_id:
        return
    from app.services.google_auth import get_credentials
    from app.services.google_sheets import delete_job_row_from_sheet
    from app.services.profile_store import get_profile

    profile = get_profile(job.user_id, db)
    spreadsheet_id = (profile.get("google_sheets_spreadsheet_id") or "").strip()
    sheet_name = (profile.get("google_sheets_tab_name") or "").strip()
    if not spreadsheet_id or not sheet_name:
        return
    url_column = (profile.get("google_sheets_url_column") or "").strip() or "Job URL"
    job_url = (job.url or "").strip()
    if not job_url:
        return
    creds = get_credentials(db, user_id=job.user_id)
    if not creds:
        return
    from googleapiclient.discovery import build

    service = build("sheets", "v4", credentials=creds)
    try:
        delete_job_row_from_sheet(
            service, spreadsheet_id, sheet_name, url_column, job_url
        )
    except Exception as e:
        logger.warning(
            "Could not remove job from Google Sheet (job_id=%s): %s", job.id, e
        )


@router.patch("/{job_id}")
def update_job(
    job_id: int,
    data: UpdateJobRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    verify_csrf(request)
    job = _get_user_job(db, user_id, job_id)
    old_status = job.status
    if data.status is not None:
        job.status = data.status
        if job.user_id:
            log_status_change(db, user_id, job_id, old_status, job.status)
            update_timestamp_fields(db, job, job.status)
    if data.rejection_reason is not None:
        job.rejection_reason = data.rejection_reason
    if data.company is not None:
        job.company = data.company
    if data.role is not None:
        job.role = data.role
    if data.location is not None:
        job.location = data.location
    if data.source_platform is not None:
        job.source_platform = data.source_platform
    if data.work_arrangement is not None:
        job.work_arrangement = data.work_arrangement
    if data.raw_body is not None:
        saved_desc = _persist_job_raw_body(job, data.raw_body)
    else:
        saved_desc = None
    db.commit()
    db.refresh(job)
    _sync_job_to_sheet_if_configured(job, db)
    out = _job_to_response(job)
    if saved_desc is not None:
        out.update(_description_stats_from_raw_body(saved_desc))
    return out


@router.post("/{job_id}/extract")
def re_extract_job(
    job_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    verify_csrf(request)
    job = _get_user_job(db, user_id, job_id)
    import json
    job_json = _load_job_json(job)
    if job_json is None:
        job_json = {
            "url": job.url,
            "company": job.company,
            "role": job.role,
            "location": job.location,
            "raw_body": "",
            "keywords": job.keywords_json or [],
            "source": job.source or "",
        }
    raw = job_json.get("raw_body") or ""
    if job.url:
        try:
            job_json = url_to_job_json(job.url, raw)
        except Exception:
            job_json = paste_only_to_job_json(raw) if raw else job_json
    else:
        job_json = paste_only_to_job_json(raw) if raw else job_json
    job_json["slug"] = job.slug
    job_md = job_json_to_markdown(job_json)
    save_job_to_disk(job.slug, job_json, job_md)
    if storage_svc.use_storage() and job.user_id:
        try:
            storage_svc.upload_job_files(job.user_id, job.slug, job_json, job_md)
        except Exception:
            pass
    job.company = job_json.get("company") or job.company
    job.role = job_json.get("role") or job.role
    job.location = job_json.get("location") or job.location
    job.keywords_json = job_json.get("keywords")
    db.commit()
    db.refresh(job)
    return _job_to_response(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    verify_csrf(request)
    job = _get_user_job(db, user_id, job_id)
    slug = job.slug
    _remove_job_from_sheet_if_configured(job, db)
    db.delete(job)
    db.commit()
    job_dir = ensure_safe_relative_path(get_settings().jobkit_jobs_dir, slug)
    if job_dir.exists():
        shutil.rmtree(job_dir)
    return None
