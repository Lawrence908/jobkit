"""Heuristic matching + LLM refinement for resume/cover letter/notes."""
import json
import logging
from pathlib import Path

from app.core.config import get_settings
from app.services.llm_provider import chat_completion
from app.services.truth_store import get_projects, get_resume_base, get_skills
from app.services.profile_store import get_profile
from app.utils.files import ensure_safe_relative_path

logger = logging.getLogger(__name__)


def _normalize_keywords(job_keywords: list[str]) -> set[str]:
    return {k.lower().strip() for k in job_keywords if k.strip()}


def score_project(project: dict, job_keywords: set[str]) -> int:
    """Score a project by tag/keyword overlap with job."""
    score = 0
    tags = set()
    if isinstance(project.get("tags"), list):
        tags = { str(t).lower() for t in project["tags"] }
    if isinstance(project.get("tech_stack"), list):
        for t in project["tech_stack"]:
            tags.add(str(t).lower())
    name_lower = (project.get("name") or "").lower()
    desc_lower = (project.get("description") or "").lower()
    for k in job_keywords:
        if k in tags:
            score += 2
        if k in name_lower or k in desc_lower:
            score += 1
    return score


def select_projects(job_keywords: list[str], length: str) -> list[dict]:
    """Select and rank projects by relevance. length: '1 page' -> fewer, '2 pages' -> more."""
    projects = get_projects()
    keywords = _normalize_keywords(job_keywords)
    scored = [(score_project(p, keywords), p) for p in projects]
    scored.sort(key=lambda x: -x[0])
    max_projects = 3 if length == "1 page" else 6
    return [p for _, p in scored[:max_projects]]


def generate_artifacts(
    job_slug: str,
    job_json: dict,
    tone: str,
    focus: str,
    length: str,
) -> tuple[str, str, str]:
    """Generate resume.md, cover_letter.md, notes.md content via LLM. Returns (resume_md, cover_letter_md, notes_md)."""
    resume_base = get_resume_base()
    profile = get_profile()
    skills = get_skills()
    selected = select_projects(job_json.get("keywords") or [], length)
    job_desc = (job_json.get("raw_body") or "")[:12000]
    ats = job_json.get("ats") or {}
    context = {
        "resume_base": resume_base,
        "profile": profile,
        "skills": skills,
        "selected_projects": selected,
        "job": {
            "company": job_json.get("company"),
            "role": job_json.get("role"),
            "description": job_desc,
        },
        "ats": ats,
        "tone": tone,
        "focus": focus,
        "length": length,
    }
    context_str = json.dumps(context, indent=2)[:15000]
    system = """You are a resume and cover letter writer. You must ONLY use facts from the provided resume_base, selected_projects, and (if present) skills. Do not invent employers, dates, or metrics. Any number or claim must appear in the source data. Use the skills data to align technical wording with the job where it matches the candidate's real experience. Output valid markdown. Be concise for 1 page, more detailed for 2 pages.
When a "profile" object is provided, use its name, email, phone, linkedin for contact and any "pitch" text where appropriate in the cover letter.
When an "ats" object is provided, use it to improve ATS (applicant tracking system) match: mirror the listed action_verbs in bullet points where accurate, weave in key_phrases from the job where they fit your real experience, and align wording with education/years_experience when true. Do not lie; only use ATS signals that genuinely apply to the candidate's background."""

    # Resume
    resume_prompt = f"""Using ONLY the data below, write a tailored resume in markdown for this job. Tone: {tone}. Focus: {focus}. Length: {length}. No invented facts. Use the "ats" signals (action_verbs, key_phrases) to phrase bullets so they match the job description where accurate.\n\n{context_str}"""
    resume_md = chat_completion([{"role": "system", "content": system}, {"role": "user", "content": resume_prompt}])

    # Cover letter
    cover_prompt = f"""Using ONLY the data below, write a short cover letter in markdown for this role at this company. Tone: {tone}. No invented facts. Where relevant, use the "ats" action_verbs and key_phrases to echo the job language.\n\n{context_str}"""
    cover_md = chat_completion([{"role": "system", "content": system}, {"role": "user", "content": cover_prompt}])

    # Notes
    notes_prompt = f"""Given the job and the resume data, output a brief markdown notes document with: 1) Keywords to emphasize, 2) Interview prep talking points, 3) Gaps/risks to address. Use only info from the context.\n\n{context_str}"""
    notes_md = chat_completion([{"role": "system", "content": system}, {"role": "user", "content": notes_prompt}])

    return resume_md, cover_md, notes_md


def write_generated_artifacts(
    job_slug: str,
    resume_md: str,
    cover_md: str,
    notes_md: str,
) -> Path:
    """Write resume.md, cover_letter.md, notes.md under JOBKIT_JOBS_DIR/<slug>/generated/."""
    settings = get_settings()
    base = ensure_safe_relative_path(settings.jobkit_jobs_dir, job_slug, "generated")
    base.mkdir(parents=True, exist_ok=True)
    (base / "resume.md").write_text(resume_md, encoding="utf-8")
    (base / "cover_letter.md").write_text(cover_md, encoding="utf-8")
    (base / "notes.md").write_text(notes_md, encoding="utf-8")
    return base
