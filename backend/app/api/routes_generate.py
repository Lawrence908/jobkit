"""Generate and render artifacts."""
import json
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, verify_csrf
from app.core.config import get_settings
from app.db.session import get_db
from app.db.models import Job, Artifact, GoogleToken
from app.services.tailor import generate_artifacts, write_generated_artifacts, select_projects
from app.services.render import render_job_pdfs
from app.services.google_auth import get_credentials
from app.services.google_drive import upload_file, ensure_folder
from app.services.google_sheets import default_column_map, get_header_row, get_row, sync_job_to_sheet
from app.utils.files import ensure_safe_relative_path

router = APIRouter(prefix="/api/jobs", tags=["generate"])


def _build_sheet_column_map(settings) -> dict:
    """Build column map from settings; use defaults so row order matches common sheet headers."""
    column_map = {}
    if settings.google_sheets_column_company:
        column_map["company"] = settings.google_sheets_column_company
    if settings.google_sheets_column_role:
        column_map["role"] = settings.google_sheets_column_role
    if settings.google_sheets_column_status:
        column_map["status"] = settings.google_sheets_column_status
    if settings.google_sheets_column_job_url:
        column_map["job_url"] = settings.google_sheets_column_job_url
    if settings.google_sheets_column_link_to_job_req:
        column_map["link_to_job_req"] = settings.google_sheets_column_link_to_job_req
    if settings.google_sheets_column_date_submitted:
        column_map["date_submitted"] = settings.google_sheets_column_date_submitted
    if settings.google_sheets_column_resume_link:
        column_map["resume_link"] = settings.google_sheets_column_resume_link
    if settings.google_sheets_column_cover_link:
        column_map["cover_link"] = settings.google_sheets_column_cover_link
    if settings.google_sheets_column_notes_link:
        column_map["notes_link"] = settings.google_sheets_column_notes_link
    if not column_map:
        column_map = default_column_map()
    return column_map


class GenerateRequest(BaseModel):
    tone: str = "neutral"
    focus: str = "full-stack"
    length: str = "1 page"


def _load_job_json(job: Job) -> dict:
    settings = get_settings()
    job_dir = ensure_safe_relative_path(settings.jobkit_jobs_dir, job.slug)
    json_path = job_dir / "job.json"
    if not json_path.exists():
        raise HTTPException(status_code=400, detail="Job data not found on disk")
    return json.loads(json_path.read_text(encoding="utf-8"))


def _generated_dir(job: Job) -> Path:
    return ensure_safe_relative_path(get_settings().jobkit_jobs_dir, job.slug, "generated")


_GENERATED_FILES = ("resume", "cover_letter", "notes")  # keys; files are resume.md, cover_letter.md, notes.md


@router.get("/{job_id}/generated")
def get_generated(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_user)],
):
    """Return raw markdown for generated resume, cover letter, and notes (null if file missing)."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    gen_dir = _generated_dir(job)
    out = {}
    for key in _GENERATED_FILES:
        path = gen_dir / f"{key}.md"
        out[key] = path.read_text(encoding="utf-8") if path.exists() else None
    return out


class GeneratedUpdateBody(BaseModel):
    content: str


@router.put("/{job_id}/generated/{doc_key}")
def update_generated(
    job_id: int,
    doc_key: str,
    data: GeneratedUpdateBody,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_user)],
):
    """Update one generated document (resume, cover_letter, or notes)."""
    if doc_key not in _GENERATED_FILES:
        raise HTTPException(status_code=400, detail="doc_key must be resume, cover_letter, or notes")
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    gen_dir = _generated_dir(job)
    filename = "cover_letter.md" if doc_key == "cover_letter" else f"{doc_key}.md"
    path = gen_dir / filename
    gen_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(data.content, encoding="utf-8")
    return {"ok": True, "doc": doc_key}


@router.get("/{job_id}/tailor-preview")
def tailor_preview(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_user)],
):
    """Return keywords and which projects would be selected for tailoring (for UI preview)."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    keywords = job.keywords_json or []
    selected = select_projects(keywords, "2 pages")  # show up to 6 projects
    return {
        "keywords": keywords,
        "selected_projects": [{"name": p.get("name"), "description": (p.get("description") or "")[:120]} for p in selected],
    }


@router.post("/{job_id}/generate")
def generate(
    job_id: int,
    request: Request,
    data: GenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_user)],
):
    verify_csrf(request)
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job_json = _load_job_json(job)
    try:
        resume_md, cover_md, notes_md = generate_artifacts(
            job.slug,
            job_json,
            data.tone,
            data.focus,
            data.length,
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise HTTPException(
                status_code=502,
                detail="LLM API key invalid or missing. Set LLM_API_KEY in the backend environment.",
            ) from e
        raise HTTPException(status_code=502, detail=f"Generation failed: {e!s}") from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Generation failed: {e!s}") from e
    write_generated_artifacts(job.slug, resume_md, cover_md, notes_md)
    settings = get_settings()
    rel = f"{job.slug}/generated"
    for art_type, name in [("resume_md", "resume.md"), ("cover_letter_md", "cover_letter.md"), ("notes_md", "notes.md")]:
        path_str = f"{rel}/{name}"
        existing = db.query(Artifact).filter(Artifact.job_id == job_id, Artifact.type == art_type).first()
        if existing:
            existing.path = path_str
            db.add(existing)
        else:
            db.add(Artifact(job_id=job_id, type=art_type, path=path_str))
    db.commit()
    return {"ok": True, "message": "Generated resume.md, cover_letter.md, notes.md"}


def _do_render_pdfs(job_id: int, job_slug: str) -> None:
    """Background task: render PDFs and update DB."""
    from app.db.session import SessionLocal
    try:
        results = render_job_pdfs(job_slug)
        db = SessionLocal()
        try:
            for art_type, pdf_path in results:
                rel = f"outputs/{job_slug}/{pdf_path.name}"
                existing = db.query(Artifact).filter(Artifact.job_id == job_id, Artifact.type == art_type).first()
                if existing:
                    existing.path = rel
                    db.add(existing)
                else:
                    db.add(Artifact(job_id=job_id, type=art_type, path=rel))
            db.commit()
        finally:
            db.close()
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("PDF render failed: %s", e)


@router.post("/{job_id}/render")
def render(
    job_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_user)],
):
    verify_csrf(request)
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    generated_dir = ensure_safe_relative_path(get_settings().jobkit_jobs_dir, job.slug, "generated")
    if not (generated_dir / "resume.md").exists():
        raise HTTPException(status_code=400, detail="Generate artifacts first (resume.md not found)")
    background_tasks.add_task(_do_render_pdfs, job_id, job.slug)
    return {"ok": True, "message": "PDF rendering started in background"}


@router.get("/{job_id}/artifacts")
def list_artifacts(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_user)],
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    artifacts = db.query(Artifact).filter(Artifact.job_id == job_id).all()
    base_url = "/api/jobs"
    out = []
    for a in artifacts:
        out.append({
            "id": a.id,
            "type": a.type,
            "path": a.path,
            "drive_link": a.drive_link,
            "download_url": f"{base_url}/{job_id}/artifacts/{a.id}/download" if a.path else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return out


@router.get("/{job_id}/artifacts/{artifact_id}/download")
def download_artifact(
    job_id: int,
    artifact_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_user)],
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    art = db.query(Artifact).filter(Artifact.id == artifact_id, Artifact.job_id == job_id).first()
    if not art or not art.path:
        raise HTTPException(status_code=404, detail="Artifact not found")
    settings = get_settings()
    if art.path.startswith("outputs/"):
        base = settings.jobkit_outputs_dir
        rel = art.path.replace("outputs/", "", 1)
    else:
        base = settings.jobkit_jobs_dir
        rel = art.path
    full_path = ensure_safe_relative_path(base, *rel.split("/"))
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    name = full_path.name
    media_type = "application/pdf" if name.endswith(".pdf") else "application/octet-stream"
    return FileResponse(full_path, filename=name, media_type=media_type)


@router.post("/{job_id}/upload-and-log")
def upload_and_log(
    job_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_user)],
):
    verify_csrf(request)
    token_row = db.query(GoogleToken).filter(GoogleToken.provider == "google").first()
    if not token_row:
        raise HTTPException(status_code=400, detail="Connect Google first (OAuth)")
    creds = get_credentials(db)
    if not creds:
        raise HTTPException(status_code=400, detail="Invalid stored token; reconnect Google")
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    settings = get_settings()
    jobs_dir = settings.jobkit_jobs_dir
    outputs_dir = settings.jobkit_outputs_dir
    root_folder_id = settings.google_drive_root_folder_id
    if not root_folder_id:
        root_folder_id = ensure_folder(creds, None, "JobKit")
    folder_name = f"{job.company or 'Unknown'}-{job.role or 'Role'}"
    folder_id = ensure_folder(creds, root_folder_id, folder_name)
    artifacts = db.query(Artifact).filter(Artifact.job_id == job_id).all()
    resume_link = ""
    cover_link = ""
    notes_link = ""
    for art in artifacts:
        if art.path.startswith("outputs/"):
            base = outputs_dir
            rel = art.path.replace("outputs/", "", 1)
        else:
            base = jobs_dir
            rel = art.path
        path = ensure_safe_relative_path(base, *rel.split("/"))
        if not path.exists():
            continue
        mime = "application/pdf" if path.suffix == ".pdf" else "text/markdown"
        fid, link = upload_file(creds, path, path.name, mime, folder_id)
        art.drive_file_id = fid
        art.drive_link = link
        db.add(art)
        if art.type == "resume_pdf" or art.type == "resume_md":
            resume_link = link
        elif art.type == "cover_letter_pdf" or art.type == "cover_letter_md":
            cover_link = link
        elif art.type == "notes_md":
            notes_link = link
    db.commit()
    spreadsheet_id = settings.google_sheets_spreadsheet_id
    sheet_name = settings.google_sheets_tab_name
    url_col = settings.google_sheets_url_column
    if spreadsheet_id and sheet_name:
        from googleapiclient.discovery import build
        service = build("sheets", "v4", credentials=creds)
        column_map = _build_sheet_column_map(settings)
        try:
            sync_job_to_sheet(
                service,
                spreadsheet_id,
                sheet_name,
                url_col,
                job,
                resume_link,
                cover_link,
                notes_link,
                column_map,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "resume_link": resume_link, "cover_letter_link": cover_link, "notes_link": notes_link}
