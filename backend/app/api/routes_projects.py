"""Projects API (CRUD for user projects used in tailoring)."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, verify_csrf
from app.db.session import get_db
from app.db.models import Project
from app.core.config import get_settings

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _project_to_dict(p: Project) -> dict:
    return {
        "id": p.id,
        "name": p.name or "",
        "description": p.description or "",
        "link": p.link or "",
        "status": p.status or "",
        "dates": p.dates or "",
        "tags": p.tags or [],
        "tech_stack": p.tech_stack or [],
        "bullets": p.bullets or [],
    }


class ProjectCreate(BaseModel):
    name: str = ""
    description: str = ""
    link: str = ""
    status: str = ""
    dates: str = ""
    tags: list[str] | None = None
    tech_stack: list[str] | None = None
    bullets: list[str] | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    link: str | None = None
    status: str | None = None
    dates: str | None = None
    tags: list[str] | None = None
    tech_stack: list[str] | None = None
    bullets: list[str] | None = None


@router.get("")
def list_projects(
    user_id: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if not get_settings().use_postgres():
        from app.services.truth_store import get_projects
        return get_projects()
    rows = db.query(Project).filter(Project.user_id == user_id).order_by(Project.id).all()
    return [_project_to_dict(p) for p in rows]


@router.post("")
def create_project(
    request: Request,
    data: ProjectCreate,
    user_id: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    verify_csrf(request)
    if not get_settings().use_postgres():
        raise HTTPException(status_code=501, detail="Projects are file-based when not using Postgres.")
    p = Project(
        user_id=user_id,
        name=data.name,
        description=data.description,
        link=data.link,
        status=data.status,
        dates=data.dates,
        tags=data.tags or [],
        tech_stack=data.tech_stack or [],
        bullets=data.bullets or [],
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _project_to_dict(p)


@router.get("/{project_id}")
def get_project(
    project_id: int,
    user_id: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if not get_settings().use_postgres():
        raise HTTPException(status_code=501, detail="Use GET /api/projects for file-based list.")
    p = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return _project_to_dict(p)


@router.put("/{project_id}")
def update_project(
    request: Request,
    project_id: int,
    data: ProjectUpdate,
    user_id: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    verify_csrf(request)
    if not get_settings().use_postgres():
        raise HTTPException(status_code=501, detail="Projects are file-based when not using Postgres.")
    p = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    updates = data.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(p, k, v)
    db.add(p)
    db.commit()
    db.refresh(p)
    return _project_to_dict(p)


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    request: Request,
    user_id: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    verify_csrf(request)
    if not get_settings().use_postgres():
        raise HTTPException(status_code=501, detail="Projects are file-based when not using Postgres.")
    p = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(p)
    db.commit()
    return {"ok": True}
