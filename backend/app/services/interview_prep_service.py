"""Interview prep generation: build context, call LLM, store structured prep and markdown."""
import json
import logging
import re
from typing import TYPE_CHECKING, Any

from app.core.config import get_settings
from app.db.models import Artifact, InterviewPrep, Job
from app.services.llm_provider import chat_completion
from app.services.profile_store import get_profile
from app.services.resume_base_store import get_resume_base as get_resume_base_db
from app.services.tailor import select_projects
from app.services.truth_store import get_projects, get_skills
from app.utils.files import ensure_safe_relative_path

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Expected JSON keys from LLM for summary_json
PREP_JSON_KEYS = [
    "likely_questions",
    "talking_points",
    "match_analysis",
    "star_responses",
    "technical_prep",
    "questions_to_ask",
    "personal_pitch",
]

SYSTEM_PROMPT = """You are an expert interview coach. You help candidates prepare for job interviews using ONLY the facts provided: their resume/profile, projects, the job description, and any tailored resume or cover letter they generated for this job. Do not invent employers, dates, projects, or skills. All talking points and STAR examples must be grounded in the provided data.

Output a single valid JSON object (no markdown code fence, no extra text) with exactly these keys:
- "likely_questions": object with keys: general, why_company, technical, behavioral, project_based, resume_challenges, gap_weakness, situational. Each value is an array of strings (questions).
- "talking_points": object with the same category keys as likely_questions; each value is an array of short strings (bullet points the candidate can use).
- "match_analysis": object with keys: strongest_alignment (array of strings), weakest_alignment (array of strings), likely_probed_areas (array of strings), missing_keywords (array of strings).
- "star_responses": array of objects with keys: prompt (the question), situation, task, action, result (all strings; based on real projects/experience only).
- "technical_prep": object with keys: topics_to_review (array), tools_frameworks (array), system_design_themes (array), coding_areas (array). Omit or empty if role is not technical.
- "questions_to_ask": array of strings (questions the candidate can ask the employer).
- "personal_pitch": string (a short "tell me about yourself" draft tailored to this job).

Use only information from the context. Be concise. For STAR responses, reference the candidate's actual projects and roles by name."""


def build_prep_context(
    job: Job,
    job_json: dict[str, Any],
    user_id: str,
    db: "Session",
    resume_md: str | None = None,
    cover_md: str | None = None,
) -> dict[str, Any]:
    """Assemble context for interview prep: job, profile, resume, skills, projects, optional tailored docs."""
    profile = get_profile(user_id, db)
    resume_base = get_resume_base_db(user_id, db)
    skills = get_skills(user_id, db)
    keywords = job_json.get("keywords") or []
    selected_projects = select_projects(keywords, "2 pages", user_id, db)
    job_desc = (job_json.get("raw_body") or "")[:12000]
    context = {
        "job": {
            "company": job_json.get("company"),
            "role": job_json.get("role"),
            "location": job_json.get("location"),
            "description": job_desc,
        },
        "profile": profile,
        "resume_base": resume_base,
        "skills": skills,
        "selected_projects": selected_projects,
        "tailored_resume_excerpt": (resume_md or "")[:4000] if resume_md else None,
        "tailored_cover_excerpt": (cover_md or "")[:2000] if cover_md else None,
    }
    return context


def _extract_json_from_response(text: str) -> dict[str, Any]:
    """Try to parse JSON from LLM response; strip code fences if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```\w*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    return json.loads(cleaned)


def _summary_to_markdown(data: dict[str, Any]) -> str:
    """Turn structured summary_json into readable markdown."""
    lines = []

    def add_heading(t: str) -> None:
        lines.append(f"\n## {t}\n")

    def add_list(items: list[str]) -> None:
        for x in items:
            if isinstance(x, str) and x.strip():
                lines.append(f"- {x}")
        lines.append("")

    pitch = data.get("personal_pitch")
    if pitch:
        add_heading("Personal pitch (Tell me about yourself)")
        lines.append(pitch.strip())
        lines.append("")

    q = data.get("likely_questions") or {}
    if q:
        add_heading("Likely interview questions")
        for category, questions in q.items():
            if isinstance(questions, list) and questions:
                lines.append(f"### {category.replace('_', ' ').title()}")
                add_list(questions)

    tp = data.get("talking_points") or {}
    if tp:
        add_heading("Suggested talking points")
        for category, points in tp.items():
            if isinstance(points, list) and points:
                lines.append(f"### {category.replace('_', ' ').title()}")
                add_list(points)

    ma = data.get("match_analysis") or {}
    if ma:
        add_heading("Match analysis")
        for key in ("strongest_alignment", "weakest_alignment", "likely_probed_areas", "missing_keywords"):
            arr = ma.get(key)
            if isinstance(arr, list) and arr:
                lines.append(f"**{key.replace('_', ' ').title()}**")
                add_list(arr)

    star = data.get("star_responses") or []
    if star:
        add_heading("STAR response suggestions")
        for i, item in enumerate(star, 1):
            if isinstance(item, dict):
                lines.append(f"### {i}. {item.get('prompt', 'Behavioral question')}")
                for k in ("situation", "task", "action", "result"):
                    v = item.get(k)
                    if v:
                        lines.append(f"**{k.title()}:** {v}")
                lines.append("")

    tech = data.get("technical_prep") or {}
    if tech and any(tech.get(k) for k in ("topics_to_review", "tools_frameworks", "system_design_themes", "coding_areas")):
        add_heading("Technical prep")
        for key in ("topics_to_review", "tools_frameworks", "system_design_themes", "coding_areas"):
            arr = tech.get(key)
            if isinstance(arr, list) and arr:
                lines.append(f"**{key.replace('_', ' ').title()}**")
                add_list(arr)

    qta = data.get("questions_to_ask") or []
    if qta:
        add_heading("Questions to ask the employer")
        add_list(qta)

    return "\n".join(lines).strip() or "# Interview prep\n\nNo content generated."


def generate_interview_prep(
    job_id: int,
    user_id: str,
    db: "Session",
    job: Job | None = None,
    job_json: dict[str, Any] | None = None,
) -> InterviewPrep:
    """Build context, call LLM for structured prep, persist to interview_preps and artifact. Returns the new InterviewPrep row."""
    if job is None:
        job = db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
        if not job:
            raise ValueError("Job not found")
    if job_json is None:
        from app.services import storage as storage_svc
        if storage_svc.use_storage() and job.user_id:
            try:
                job_json = storage_svc.download_job_json(job.user_id, job.slug)
            except Exception as e:
                raise ValueError("Job data not found in storage") from e
        else:
            import json as _json
            settings = get_settings()
            job_dir = ensure_safe_relative_path(settings.jobkit_jobs_dir, job.slug)
            path = job_dir / "job.json"
            if not path.exists():
                raise ValueError("Job data not found")
            job_json = _json.loads(path.read_text(encoding="utf-8"))

    resume_md = cover_md = None
    from app.services import storage as storage_svc
    if storage_svc.use_storage() and job.user_id:
        try:
            resume_md = storage_svc.download_generated_md(job.user_id, job.slug, "resume.md")
        except Exception:
            pass
        try:
            cover_md = storage_svc.download_generated_md(job.user_id, job.slug, "cover_letter.md")
        except Exception:
            pass

    context = build_prep_context(job, job_json, user_id, db, resume_md=resume_md, cover_md=cover_md)
    context_str = json.dumps(context, indent=2)[:18000]

    profile = get_profile(user_id, db)
    llm_kwargs: dict[str, Any] = {}
    if profile.get("llm_api_key"):
        llm_kwargs["provider"] = profile.get("llm_provider") or "openrouter"
        llm_kwargs["api_key"] = profile["llm_api_key"]
        llm_kwargs["model"] = (profile.get("llm_model") or "").strip()
        llm_kwargs["temperature"] = profile.get("llm_temperature")
    else:
        settings = get_settings()
        llm_kwargs["api_key"] = settings.llm_api_key

    user_prompt = f"""Using ONLY the data below, generate the interview prep JSON object as specified. Job: {job.company} – {job.role}.

{context_str}"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    response_text = chat_completion(messages, **llm_kwargs)

    try:
        summary = _extract_json_from_response(response_text)
    except json.JSONDecodeError as e:
        logger.warning("Interview prep LLM response was not valid JSON: %s", e)
        summary = {"personal_pitch": "", "likely_questions": {}, "talking_points": {}, "match_analysis": {}, "star_responses": [], "technical_prep": {}, "questions_to_ask": []}

    markdown_text = _summary_to_markdown(summary)

    # Version: next after latest for this job
    latest = db.query(InterviewPrep).filter(InterviewPrep.job_id == job_id, InterviewPrep.user_id == user_id).order_by(InterviewPrep.version.desc()).first()
    next_version = (latest.version + 1) if latest else 1

    # Optional: link to resume/cover artifacts if we used them
    source_resume_id = source_cover_id = None
    if resume_md or cover_md:
        arts = db.query(Artifact).filter(Artifact.job_id == job_id, Artifact.type.in_(["resume_md", "cover_letter_md"])).all()
        for a in arts:
            if a.type == "resume_md":
                source_resume_id = a.id
            elif a.type == "cover_letter_md":
                source_cover_id = a.id

    prep = InterviewPrep(
        user_id=user_id,
        job_id=job_id,
        version=next_version,
        markdown_text=markdown_text,
        summary_json=summary,
        source_resume_artifact_id=source_resume_id,
        source_cover_letter_artifact_id=source_cover_id,
    )
    db.add(prep)
    db.flush()

    # Store artifact (interview_prep_md)
    from app.services import storage as storage_svc
    path_str: str
    if storage_svc.use_storage() and job.user_id:
        key = storage_svc.generated_key(job.user_id, job.slug, "interview_prep.md")
        storage_svc.upload_bytes(key, markdown_text.encode("utf-8"), "text/markdown")
        path_str = key
    else:
        settings = get_settings()
        gen_dir = ensure_safe_relative_path(settings.jobkit_jobs_dir, job.slug, "generated")
        gen_dir.mkdir(parents=True, exist_ok=True)
        (gen_dir / "interview_prep.md").write_text(markdown_text, encoding="utf-8")
        path_str = f"{job.slug}/generated/interview_prep.md"

    existing_art = db.query(Artifact).filter(Artifact.job_id == job_id, Artifact.type == "interview_prep_md").first()
    if existing_art:
        existing_art.path = path_str
        db.add(existing_art)
    else:
        db.add(Artifact(job_id=job_id, user_id=user_id, type="interview_prep_md", path=path_str))

    db.commit()
    db.refresh(prep)
    return prep


def get_latest_prep(job_id: int, user_id: str, db: "Session") -> InterviewPrep | None:
    """Return the latest interview prep for this job and user, or None."""
    return (
        db.query(InterviewPrep)
        .filter(InterviewPrep.job_id == job_id, InterviewPrep.user_id == user_id)
        .order_by(InterviewPrep.version.desc())
        .first()
    )


def list_prep_versions(job_id: int, user_id: str, db: "Session") -> list[InterviewPrep]:
    """List all interview prep versions for this job, newest first."""
    return (
        db.query(InterviewPrep)
        .filter(InterviewPrep.job_id == job_id, InterviewPrep.user_id == user_id)
        .order_by(InterviewPrep.version.desc())
        .all()
    )


def get_prep_by_id(prep_id: int, job_id: int, user_id: str, db: "Session") -> InterviewPrep | None:
    """Return a specific interview prep by id if it belongs to this job and user."""
    return (
        db.query(InterviewPrep)
        .filter(InterviewPrep.id == prep_id, InterviewPrep.job_id == job_id, InterviewPrep.user_id == user_id)
        .first()
    )
