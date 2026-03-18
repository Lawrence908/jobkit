"""Interview prep generation and retrieval."""
import json
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, verify_csrf
from app.core.config import get_settings
from app.db.session import get_db
from app.db.models import Artifact, Job
from app.services import storage as storage_svc
from app.services.interview_prep_service import (
    generate_interview_prep,
    get_latest_prep,
    get_prep_by_id,
    list_prep_versions,
)
from app.services.render import md_to_html, render_pdf
from app.utils.files import ensure_safe_relative_path

router = APIRouter(prefix="/api/jobs", tags=["interview-prep"])

_CSS_PATH = Path(__file__).resolve().parent.parent / "templates" / "resume.css"


def _get_user_job(db: Session, user_id: str, job_id: int) -> Job:
    from sqlalchemy import or_
    job = db.query(Job).filter(
        Job.id == job_id,
        or_(Job.user_id == user_id, Job.user_id.is_(None)),
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _load_job_json(job: Job) -> dict:
    """Load job.json from Storage or disk. Raises if not found."""
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


@router.post("/{job_id}/interview-prep/generate")
def interview_prep_generate(
    job_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    verify_csrf(request)
    job = _get_user_job(db, user_id, job_id)
    job_json = _load_job_json(job)
    try:
        prep = generate_interview_prep(job_id, user_id, db, job=job, job_json=job_json)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise HTTPException(
                status_code=502,
                detail="LLM API key invalid or missing. Set your API key in Profile → LLM.",
            ) from e
        raise HTTPException(status_code=502, detail=f"Generation failed: {e!s}") from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Generation failed: {e!s}") from e
    return {
        "ok": True,
        "prep_id": prep.id,
        "version": prep.version,
        "message": "Interview prep generated",
    }


@router.get("/{job_id}/interview-prep")
def interview_prep_get_latest(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    job = _get_user_job(db, user_id, job_id)
    prep = get_latest_prep(job_id, user_id, db)
    if not prep:
        return {"prep": None}
    return {
        "prep": {
            "id": prep.id,
            "job_id": prep.job_id,
            "version": prep.version,
            "markdown_text": prep.markdown_text,
            "summary_json": prep.summary_json,
            "created_at": prep.created_at.isoformat() if prep.created_at else None,
            "updated_at": prep.updated_at.isoformat() if prep.updated_at else None,
        },
    }


@router.get("/{job_id}/interview-prep/versions")
def interview_prep_list_versions(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    _get_user_job(db, user_id, job_id)
    preps = list_prep_versions(job_id, user_id, db)
    return {
        "versions": [
            {
                "id": p.id,
                "version": p.version,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in preps
        ],
    }


@router.get("/{job_id}/interview-prep/{prep_id}")
def interview_prep_get_by_id(
    job_id: int,
    prep_id: int,
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    _get_user_job(db, user_id, job_id)
    prep = get_prep_by_id(prep_id, job_id, user_id, db)
    if not prep:
        raise HTTPException(status_code=404, detail="Interview prep not found")
    return {
        "prep": {
            "id": prep.id,
            "job_id": prep.job_id,
            "version": prep.version,
            "markdown_text": prep.markdown_text,
            "summary_json": prep.summary_json,
            "created_at": prep.created_at.isoformat() if prep.created_at else None,
            "updated_at": prep.updated_at.isoformat() if prep.updated_at else None,
        },
    }


def _do_render_interview_prep_pdf(
    job_id: int,
    job_slug: str,
    user_id: str,
    markdown_text: str,
) -> None:
    from app.db.session import SessionLocal
    try:
        html_content = md_to_html(markdown_text)
        settings = get_settings()
        out_dir = ensure_safe_relative_path(settings.jobkit_outputs_dir, job_slug)
        out_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = out_dir / "interview_prep.pdf"
        render_pdf(html_content, pdf_path, _CSS_PATH)
        db = SessionLocal()
        try:
            if user_id:
                path_str = storage_svc.output_pdf_key(user_id, job_slug, "interview_prep.pdf")
                if storage_svc.use_storage():
                    try:
                        storage_svc.upload_output_pdf(
                            user_id, job_slug, "interview_prep.pdf", pdf_path.read_bytes()
                        )
                    except Exception:
                        pass
            else:
                path_str = f"outputs/{job_slug}/interview_prep.pdf"
            existing = db.query(Artifact).filter(
                Artifact.job_id == job_id,
                Artifact.type == "interview_prep_pdf",
            ).first()
            if existing:
                existing.path = path_str
                db.add(existing)
            else:
                db.add(Artifact(job_id=job_id, user_id=user_id, type="interview_prep_pdf", path=path_str))
            db.commit()
        finally:
            db.close()
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Interview prep PDF render failed: %s", e)


@router.post("/{job_id}/interview-prep/{prep_id}/render-pdf")
def interview_prep_render_pdf(
    job_id: int,
    prep_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user)],
):
    verify_csrf(request)
    job = _get_user_job(db, user_id, job_id)
    prep = get_prep_by_id(prep_id, job_id, user_id, db)
    if not prep:
        raise HTTPException(status_code=404, detail="Interview prep not found")
    background_tasks.add_task(
        _do_render_interview_prep_pdf,
        job_id,
        job.slug,
        user_id,
        prep.markdown_text,
    )
    return {"ok": True, "message": "PDF rendering started in background"}
