"""Generate and render artifacts."""
import json
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, verify_csrf
from app.core.config import get_settings
from app.db.session import get_db
from app.db.models import Job, Artifact, GoogleToken
from app.services.tailor import generate_artifacts, write_generated_artifacts, select_projects
from app.services.render import render_job_pdfs, md_to_html, render_pdf, _CSS_PATH as RENDER_CSS_PATH
from app.services.google_auth import get_credentials
from app.services.google_drive import upload_file, ensure_folder
from app.services.google_sheets import default_column_map, get_header_row, get_row, sync_job_to_sheet
from app.utils.files import ensure_safe_relative_path
from app.services import storage as storage_svc

router = APIRouter(prefix="/api/jobs", tags=["generate"])


def _get_user_job(db: Session, user_id: str, job_id: int) -> Job:
    job = db.query(Job).filter(
        Job.id == job_id,
        or_(Job.user_id == user_id, Job.user_id.is_(None)),
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _build_sheet_column_map(settings) -> dict:
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


def _read_artifact_content(art, storage_svc, jobs_dir: Path, outputs_dir: Path) -> str | None:
    """Read artifact file content as string. Returns None on failure."""
    if storage_svc.is_storage_key(art.path):
        try:
            data = storage_svc.download_bytes(art.path)
            return data.decode("utf-8")
        except Exception:
            return None
    if art.path.startswith("outputs/"):
        base = outputs_dir
        rel = art.path.replace("outputs/", "", 1)
    else:
        base = jobs_dir
        rel = art.path
    path = ensure_safe_relative_path(base, *rel.split("/"))
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None


def _render_md_to_pdf_and_upload(md_content: str, creds, folder_id: str, pdf_name: str, css_path: Path | None):
    """Render markdown to PDF, upload to Drive. Returns (drive_file_id, drive_link) or (None, None)."""
    import tempfile
    try:
        html_content = md_to_html(md_content)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            try:
                render_pdf(html_content, Path(tmp.name), css_path=css_path)
                fid, link = upload_file(creds, Path(tmp.name), pdf_name, "application/pdf", folder_id)
                return (fid, link)
            finally:
                Path(tmp.name).unlink(missing_ok=True)
    except Exception:
        return (None, None)


class GenerateRequest(BaseModel):
    tone: str = "neutral"
    focus: str = "full-stack"
    length: str = "1 page"
    model: str | None = None


def _load_job_json(job: Job) -> dict:
    """Load job.json from Storage when Supabase configured, else disk. Raises if not found."""
    if storage_svc.use_storage() and job.user_id:
        try:
            return storage_svc.download_job_json(job.user_id, job.slug)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Job data not found in storage") from e
    settings = get_settings()
    job_dir = ensure_safe_relative_path(settings.jobkit_jobs_dir, job.slug)
    json_path = job_dir / "job.json"
    if not json_path.exists():
        raise HTTPException(status_code=400, detail="Job data not found")
    return json.loads(json_path.read_text(encoding="utf-8"))


def _generated_dir(job: Job) -> Path:
    return ensure_safe_relative_path(get_settings().jobkit_jobs_dir, job.slug, "generated")


_GENERATED_FILES = ("resume", "cover_letter", "notes")


@router.get("/{job_id}/generated")
def get_generated(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    job = _get_user_job(db, user_id, job_id)
    out = {}
    if storage_svc.use_storage() and job.user_id:
        for key in _GENERATED_FILES:
            name = "cover_letter.md" if key == "cover_letter" else f"{key}.md"
            try:
                out[key] = storage_svc.download_generated_md(job.user_id, job.slug, name)
            except Exception:
                out[key] = None
        return out
    gen_dir = _generated_dir(job)
    for key in _GENERATED_FILES:
        name = "cover_letter.md" if key == "cover_letter" else f"{key}.md"
        path = gen_dir / name
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
    user_id: Annotated[str, Depends(get_current_user)],
):
    if doc_key not in _GENERATED_FILES:
        raise HTTPException(status_code=400, detail="doc_key must be resume, cover_letter, or notes")
    job = _get_user_job(db, user_id, job_id)
    filename = "cover_letter.md" if doc_key == "cover_letter" else f"{doc_key}.md"
    if storage_svc.use_storage() and job.user_id:
        try:
            storage_svc.upload_bytes(
                storage_svc.generated_key(job.user_id, job.slug, filename),
                data.content.encode("utf-8"),
                "text/markdown",
            )
        except Exception:
            pass
    gen_dir = _generated_dir(job)
    gen_dir.mkdir(parents=True, exist_ok=True)
    (gen_dir / filename).write_text(data.content, encoding="utf-8")
    return {"ok": True, "doc": doc_key}


@router.get("/{job_id}/tailor-preview")
def tailor_preview(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    job = _get_user_job(db, user_id, job_id)
    keywords = job.keywords_json or []
    selected = select_projects(keywords, "2 pages", user_id, db)
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
    user_id: Annotated[str, Depends(get_current_user)],
):
    verify_csrf(request)
    job = _get_user_job(db, user_id, job_id)
    job_json = _load_job_json(job)
    try:
        resume_md, cover_md, notes_md = generate_artifacts(
            job.slug,
            job_json,
            data.tone,
            data.focus,
            data.length,
            model=data.model if (data.model and data.model.strip()) else None,
            user_id=user_id,
            db=db,
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise HTTPException(
                status_code=502,
                detail="LLM API key invalid or missing. Set your API key in Profile → LLM for generation, or LLM_API_KEY in the backend environment.",
            ) from e
        raise HTTPException(status_code=502, detail=f"Generation failed: {e!s}") from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Generation failed: {e!s}") from e
    write_generated_artifacts(job.slug, resume_md, cover_md, notes_md)
    # When user_id is set, always store artifact path as storage key (user_id/jobs/slug/generated/...) for consistency
    if job.user_id:
        path_tuples = storage_svc.generated_artifact_paths(job.user_id, job.slug)
        if storage_svc.use_storage():
            try:
                storage_svc.upload_generated_mds(job.user_id, job.slug, resume_md, cover_md, notes_md)
            except Exception:
                pass  # path still stored as storage key; download can fall back to disk
    else:
        path_tuples = None
    if path_tuples:
        for art_type, path_str in path_tuples:
            existing = db.query(Artifact).filter(Artifact.job_id == job_id, Artifact.type == art_type).first()
            if existing:
                existing.path = path_str
                db.add(existing)
            else:
                db.add(Artifact(job_id=job_id, user_id=user_id, type=art_type, path=path_str))
    else:
        rel = f"{job.slug}/generated"
        for art_type, name in [("resume_md", "resume.md"), ("cover_letter_md", "cover_letter.md"), ("notes_md", "notes.md")]:
            path_str = f"{rel}/{name}"
            existing = db.query(Artifact).filter(Artifact.job_id == job_id, Artifact.type == art_type).first()
            if existing:
                existing.path = path_str
                db.add(existing)
            else:
                db.add(Artifact(job_id=job_id, user_id=user_id, type=art_type, path=path_str))
    db.commit()
    return {"ok": True, "message": "Generated resume.md, cover_letter.md, notes.md"}


def _do_render_pdfs(job_id: int, job_slug: str, user_id: str) -> None:
    from app.db.session import SessionLocal
    try:
        results = render_job_pdfs(job_slug)
        db = SessionLocal()
        try:
            for art_type, pdf_path in results:
                if user_id:
                    path_str = storage_svc.output_pdf_key(user_id, job_slug, pdf_path.name)
                    if storage_svc.use_storage():
                        try:
                            storage_svc.upload_output_pdf(
                                user_id, job_slug, pdf_path.name, pdf_path.read_bytes()
                            )
                        except Exception:
                            pass  # path still storage key; download can fall back to disk
                else:
                    path_str = f"outputs/{job_slug}/{pdf_path.name}"
                existing = db.query(Artifact).filter(Artifact.job_id == job_id, Artifact.type == art_type).first()
                if existing:
                    existing.path = path_str
                    db.add(existing)
                else:
                    db.add(Artifact(job_id=job_id, user_id=user_id, type=art_type, path=path_str))
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
    user_id: Annotated[str, Depends(get_current_user)],
):
    verify_csrf(request)
    job = _get_user_job(db, user_id, job_id)
    generated_dir = ensure_safe_relative_path(get_settings().jobkit_jobs_dir, job.slug, "generated")
    if not (generated_dir / "resume.md").exists():
        raise HTTPException(status_code=400, detail="Generate artifacts first (resume.md not found)")
    background_tasks.add_task(_do_render_pdfs, job_id, job.slug, user_id)
    return {"ok": True, "message": "PDF rendering started in background"}


@router.get("/{job_id}/artifacts")
def list_artifacts(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    job = _get_user_job(db, user_id, job_id)
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
    user_id: Annotated[str, Depends(get_current_user)],
):
    job = _get_user_job(db, user_id, job_id)
    art = db.query(Artifact).filter(Artifact.id == artifact_id, Artifact.job_id == job_id).first()
    if not art or not art.path:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if storage_svc.is_storage_key(art.path):
        try:
            signed_url = storage_svc.create_signed_url(art.path, expires_in=3600)
            return RedirectResponse(url=signed_url, status_code=302)
        except Exception as e:
            raise HTTPException(status_code=404, detail="Artifact not found in storage") from e
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
    user_id: Annotated[str, Depends(get_current_user)],
):
    from app.services.profile_store import get_profile

    verify_csrf(request)
    token_row = db.query(GoogleToken).filter(
        GoogleToken.provider == "google",
        GoogleToken.user_id == user_id,
    ).first()
    if not token_row:
        raise HTTPException(status_code=400, detail="Connect Google first (OAuth)")
    creds = get_credentials(db, user_id=user_id)
    if not creds:
        raise HTTPException(status_code=400, detail="Invalid stored token; reconnect Google")
    job = _get_user_job(db, user_id, job_id)
    settings = get_settings()
    jobs_dir = settings.jobkit_jobs_dir
    outputs_dir = settings.jobkit_outputs_dir
    profile = get_profile(user_id, db)
    root_folder_id = (profile.get("google_drive_root_folder_id") or "").strip() or settings.google_drive_root_folder_id
    if not root_folder_id:
        root_folder_id = ensure_folder(creds, None, "JobKit")
    folder_name = f"{job.company or 'Unknown'}-{job.role or 'Role'}"
    folder_id = ensure_folder(creds, root_folder_id, folder_name)
    artifacts = db.query(Artifact).filter(Artifact.job_id == job_id).all()
    resume_link = ""
    cover_link = ""
    notes_link = ""
    import tempfile

    for art in artifacts:
        fid, link = None, None
        # For resume and cover letter, always upload PDF to Drive so the sheet gets PDF links (not .md).
        if art.type == "resume_md":
            md_content = _read_artifact_content(art, storage_svc, jobs_dir, outputs_dir)
            if md_content is not None:
                fid, link = _render_md_to_pdf_and_upload(
                    md_content, creds, folder_id, "resume.pdf", RENDER_CSS_PATH,
                )
        elif art.type == "cover_letter_md":
            md_content = _read_artifact_content(art, storage_svc, jobs_dir, outputs_dir)
            if md_content is not None:
                fid, link = _render_md_to_pdf_and_upload(
                    md_content, creds, folder_id, "cover_letter.pdf", RENDER_CSS_PATH,
                )
        elif storage_svc.is_storage_key(art.path):
            try:
                data = storage_svc.download_bytes(art.path)
                name = art.path.split("/")[-1]
                mime = "application/pdf" if name.endswith(".pdf") else "text/markdown"
                with tempfile.NamedTemporaryFile(delete=False, suffix=name[-4:] if "." in name else "") as tmp:
                    tmp.write(data)
                    tmp.flush()
                    fid, link = upload_file(creds, Path(tmp.name), name, mime, folder_id)
                Path(tmp.name).unlink(missing_ok=True)
            except Exception:
                continue
        else:
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
        if fid is None:
            continue
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
    spreadsheet_id = (profile.get("google_sheets_spreadsheet_id") or "").strip() or settings.google_sheets_spreadsheet_id
    sheet_name = (profile.get("google_sheets_tab_name") or "").strip() or settings.google_sheets_tab_name
    url_col = (profile.get("google_sheets_url_column") or "").strip() or settings.google_sheets_url_column or "Job URL"
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
