"""Resume base API (master resume for tailoring)."""
import io
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from weasyprint import CSS, HTML

from app.core.auth import get_current_user, verify_csrf
from app.db.session import get_db
from app.services.render import _CSS_PATH, md_to_html
from app.services.resume_base_markdown import resume_base_to_markdown
from app.services.resume_base_store import get_resume_base, save_resume_base

router = APIRouter(prefix="/api/resume", tags=["resume"])


class ResumeBaseUpdate(BaseModel):
    contact: dict | None = None
    summary: str | None = None
    highlights_of_qualifications: list[str] | None = None
    technical_snapshot: dict | None = None
    experience: list[dict] | None = None
    education: list[dict] | None = None
    certifications: list[str] | None = None


@router.get("/preview.pdf")
def resume_base_preview_pdf(
    user_id: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    WeasyPrint-rendered PDF of the resume base (same CSS as generated job resumes).
    Used on the profile page preview; requires Authorization header (fetch as blob).
    """
    data = get_resume_base(user_id, db)
    md = resume_base_to_markdown(data)
    html = md_to_html(md)
    buf = io.BytesIO()
    doc = HTML(string=html)
    if _CSS_PATH.exists():
        doc.write_pdf(buf, stylesheets=[CSS(filename=str(_CSS_PATH))])
    else:
        doc.write_pdf(buf)
    pdf_bytes = buf.getvalue()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="resume-base-preview.pdf"',
            "Cache-Control": "private, max-age=60",
        },
    )


@router.get("")
def read_resume(
    user_id: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return get_resume_base(user_id, db)


@router.put("")
def update_resume(
    request: Request,
    data: ResumeBaseUpdate,
    user_id: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    verify_csrf(request)
    current = get_resume_base(user_id, db)
    updates = data.model_dump(exclude_unset=True)
    for k, v in updates.items():
        if k in current:
            current[k] = v
    save_resume_base(user_id, current, db)
    return get_resume_base(user_id, db)
