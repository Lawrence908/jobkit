"""Job CRUD and ingestion."""
import shutil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, verify_csrf
from app.db.session import get_db
from app.db.models import Job
from app.services.ingest import ingest_job, job_json_to_markdown, save_job_to_disk, url_to_job_json, paste_only_to_job_json
from app.services.extract import extract_keywords, extract_ats_signals
from app.utils.files import job_slug, ensure_safe_relative_path
from app.core.config import get_settings

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class CreateJobRequest(BaseModel):
    url: str | None = None
    raw_text: str | None = None


class UpdateJobRequest(BaseModel):
    status: str | None = None
    company: str | None = None
    role: str | None = None
    location: str | None = None


class UpdateDescriptionRequest(BaseModel):
    raw_body: str


def _job_to_response(job: Job) -> dict:
    return {
        "id": job.id,
        "url": job.url,
        "company": job.company,
        "role": job.role,
        "location": job.location,
        "status": job.status,
        "slug": job.slug,
        "keywords": job.keywords_json or [],
        "source": job.source,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_job(
    request: Request,
    data: CreateJobRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_user)],
):
    verify_csrf(request)
    if not data.url and not data.raw_text:
        raise HTTPException(status_code=400, detail="Provide url or raw_text")
    try:
        job_json = ingest_job(data.url, data.raw_text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    slug = job_json["slug"]
    # Persist to DB
    job = Job(
        url=job_json.get("url"),
        company=job_json.get("company") or "",
        role=job_json.get("role") or "",
        location=job_json.get("location") or "",
        status="New",
        slug=slug,
        keywords_json=job_json.get("keywords"),
        source=job_json.get("source") or "",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_to_response(job)


@router.get("")
def list_jobs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_user)],
):
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    return [_job_to_response(j) for j in jobs]


def _description_stats_from_disk(job: Job) -> dict:
    """Load job.json and return description_word_count and description_preview for UI."""
    import json
    settings = get_settings()
    job_dir = ensure_safe_relative_path(settings.jobkit_jobs_dir, job.slug)
    job_json_path = job_dir / "job.json"
    if not job_json_path.exists():
        return {}
    try:
        job_json = json.loads(job_json_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    raw = (job_json.get("raw_body") or "").strip()
    word_count = len(raw.split()) if raw else 0
    preview = (raw[:400] + "…") if len(raw) > 400 else raw
    return {
        "description_word_count": word_count,
        "description_preview": preview or None,
        "raw_body": raw or None,
    }


@router.get("/{job_id}")
def get_job(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_user)],
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    out = _job_to_response(job)
    out.update(_description_stats_from_disk(job))
    return out


@router.post("/{job_id}/update-description")
def update_job_description(
    job_id: int,
    request: Request,
    data: UpdateDescriptionRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_user)],
):
    """Update the job's stored description (raw_body) and re-extract keywords/ATS from role + description."""
    verify_csrf(request)
    import json
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    settings = get_settings()
    job_dir = ensure_safe_relative_path(settings.jobkit_jobs_dir, job.slug)
    job_dir.mkdir(parents=True, exist_ok=True)
    job_json_path = job_dir / "job.json"
    if job_json_path.exists():
        job_json = json.loads(job_json_path.read_text(encoding="utf-8"))
    else:
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
    raw_body = (data.raw_body or "").strip()
    job_json["raw_body"] = raw_body
    combined = f"{job.role or ''}\n{raw_body}"
    job_json["keywords"] = extract_keywords(combined)
    job_json["ats"] = extract_ats_signals(combined)
    job_md = job_json_to_markdown(job_json)
    save_job_to_disk(job.slug, job_json, job_md)
    job.keywords_json = job_json["keywords"]
    db.commit()
    db.refresh(job)
    out = _job_to_response(job)
    out.update(_description_stats_from_disk(job))
    return out


def _sync_job_to_sheet_if_configured(job: Job, db: Session) -> None:
    """If Google Sheets is configured, update or append the row for this job."""
    settings = get_settings()
    if not settings.google_sheets_spreadsheet_id or not settings.google_sheets_tab_name:
        return
    from app.db.models import Artifact
    from app.services.google_auth import get_credentials
    from app.services.google_sheets import sync_job_to_sheet
    from app.api.routes_generate import _build_sheet_column_map

    creds = get_credentials(db)
    if not creds:
        return
    resume_link = cover_link = notes_link = ""
    for art in db.query(Artifact).filter(Artifact.job_id == job.id):
        if art.drive_link:
            if art.type in ("resume_pdf", "resume_md"):
                resume_link = art.drive_link
            elif art.type in ("cover_letter_pdf", "cover_letter_md"):
                cover_link = art.drive_link
            elif art.type == "notes_md":
                notes_link = art.drive_link
    from googleapiclient.discovery import build
    service = build("sheets", "v4", credentials=creds)
    column_map = _build_sheet_column_map(settings)
    try:
        sync_job_to_sheet(
            service,
            settings.google_sheets_spreadsheet_id,
            settings.google_sheets_tab_name,
            settings.google_sheets_url_column,
            job,
            resume_link,
            cover_link,
            notes_link,
            column_map,
        )
    except Exception:
        pass  # Don't fail job update if sheet sync fails


@router.patch("/{job_id}")
def update_job(
    job_id: int,
    data: UpdateJobRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_user)],
):
    verify_csrf(request)
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if data.status is not None:
        job.status = data.status
    if data.company is not None:
        job.company = data.company
    if data.role is not None:
        job.role = data.role
    if data.location is not None:
        job.location = data.location
    db.commit()
    db.refresh(job)
    _sync_job_to_sheet_if_configured(job, db)
    return _job_to_response(job)


@router.post("/{job_id}/extract")
def re_extract_job(
    job_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_user)],
):
    verify_csrf(request)
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    import json
    settings = get_settings()
    job_dir = ensure_safe_relative_path(settings.jobkit_jobs_dir, job.slug)
    job_json_path = job_dir / "job.json"
    if job_json_path.exists():
        job_json = json.loads(job_json_path.read_text(encoding="utf-8"))
    else:
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
    _: Annotated[str, Depends(get_current_user)],
):
    """Delete the job, its artifacts, and its folder on disk."""
    verify_csrf(request)
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    slug = job.slug
    db.delete(job)
    db.commit()
    job_dir = ensure_safe_relative_path(get_settings().jobkit_jobs_dir, slug)
    if job_dir.exists():
        shutil.rmtree(job_dir)
    return None
