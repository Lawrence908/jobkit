"""SQLAlchemy models: Job, Artifact, GoogleToken, InviteCode, Profile, ResumeBase, UserSkills, Project, JobStatusEvent, InterviewPrep."""
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True, index=True)
    company: Mapped[str] = mapped_column(String(512), default="", index=True)
    role: Mapped[str] = mapped_column(String(512), default="", index=True)
    location: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(64), default="Have Not Applied", index=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    slug: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    keywords_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(128), default="")
    source_platform: Mapped[str | None] = mapped_column(String(64), nullable=True)
    work_arrangement: Mapped[str | None] = mapped_column(String(64), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    interview_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    offered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    artifacts: Mapped[list["Artifact"]] = relationship("Artifact", back_populates="job", cascade="all, delete-orphan")
    status_events: Mapped[list["JobStatusEvent"]] = relationship("JobStatusEvent", back_populates="job", cascade="all, delete-orphan")
    interview_preps: Mapped[list["InterviewPrep"]] = relationship("InterviewPrep", back_populates="job", cascade="all, delete-orphan")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(64), index=True)
    path: Mapped[str] = mapped_column(String(1024))
    drive_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    drive_link: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["Job"] = relationship("Job", back_populates="artifacts")


class GoogleToken(Base):
    __tablename__ = "google_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), default="google")
    encrypted_refresh_token: Mapped[str] = mapped_column(Text)
    scopes: Mapped[str] = mapped_column(String(1024), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(256), default="")
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), default="")
    email: Mapped[str] = mapped_column(String(256), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    linkedin: Mapped[str] = mapped_column(String(512), default="")
    website: Mapped[str] = mapped_column(String(512), default="")
    github: Mapped[str] = mapped_column(String(512), default="")
    pitch: Mapped[str] = mapped_column(Text, default="")
    default_tone: Mapped[str] = mapped_column(String(64), default="neutral")
    default_focus: Mapped[str] = mapped_column(String(64), default="full-stack")
    default_length: Mapped[str] = mapped_column(String(64), default="1 page")
    llm_provider: Mapped[str] = mapped_column(String(64), default="openrouter")
    llm_api_key: Mapped[str] = mapped_column(Text, default="")
    llm_model: Mapped[str] = mapped_column(String(256), default="anthropic/claude-sonnet-4.6")
    llm_temperature: Mapped[float] = mapped_column(Float, default=0.2)
    # Per-user Google integration (optional). When set, Drive/Sheets use these instead of server .env.
    google_drive_root_folder_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    google_sheets_spreadsheet_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    google_sheets_tab_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    google_sheets_url_column: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ResumeBase(Base):
    __tablename__ = "resume_bases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    contact: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    highlights: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)  # list of strings
    technical_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    experience: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)  # list of {role, company, dates, bullets}
    education: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    certifications: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)  # list of strings
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserSkills(Base):
    __tablename__ = "user_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    categories: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # {category_name: [strings]}
    items: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)  # flat list of keywords
    skills_spotlight: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)  # subset shown on profile; null = show all
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    link: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(128), default="")
    dates: Mapped[str] = mapped_column(String(128), default="")
    tags: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    tech_stack: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    bullets: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class JobStatusEvent(Base):
    __tablename__ = "job_status_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    old_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_status: Mapped[str] = mapped_column(String(64))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped["Job"] = relationship("Job", back_populates="status_events")


class InterviewPrep(Base):
    __tablename__ = "interview_preps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    markdown_text: Mapped[str] = mapped_column(Text)
    summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source_resume_artifact_id: Mapped[int | None] = mapped_column(ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True)
    source_cover_letter_artifact_id: Mapped[int | None] = mapped_column(ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    job: Mapped["Job"] = relationship("Job", back_populates="interview_preps")
