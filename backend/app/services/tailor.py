"""Heuristic matching + LLM refinement for resume/cover letter/notes."""
import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.core.config import get_settings
from app.services.llm_provider import chat_completion
from app.services import exemplar_store
from app.services.exemplar_store import ROLE_FAMILIES
from app.services.truth_store import get_projects, get_skills
from app.services.profile_store import get_profile
from app.services.resume_base_store import get_resume_base as get_resume_base_db
from app.services.resume_base_markdown import resume_base_to_markdown
from app.utils.files import ensure_safe_relative_path

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

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


def select_projects(
    job_keywords: list[str],
    length: str,
    user_id: str | None = None,
    db: "Session | None" = None,
) -> list[dict]:
    """Select and rank projects by relevance. length: '1 page' -> fewer, '2 pages' -> more."""
    projects = get_projects(user_id, db)
    keywords = _normalize_keywords(job_keywords)
    scored = [(score_project(p, keywords), p) for p in projects]
    scored.sort(key=lambda x: -x[0])
    max_projects = 3 if length == "1 page" else 6
    return [p for _, p in scored[:max_projects]]


def _flatten_skills(skills: dict[str, Any] | list[Any]) -> list[str]:
    """Flatten skills from get_skills() shape (categories + items) to list of strings."""
    out: list[str] = []
    if isinstance(skills, list):
        for x in skills:
            s = (x if isinstance(x, str) else str(x)).strip()
            if s:
                out.append(s)
        return out
    if not isinstance(skills, dict):
        return out
    for key, val in (skills.get("categories") or {}).items():
        if isinstance(val, list):
            for x in val:
                s = (x if isinstance(x, str) else str(x)).strip()
                if s:
                    out.append(s)
        elif val:
            out.append(str(val).strip())
    for x in skills.get("items") or []:
        s = (x if isinstance(x, str) else str(x)).strip()
        if s:
            out.append(s)
    return out


def score_skill(skill: str, job_keywords: set[str]) -> int:
    """Score a skill string by overlap with job keywords."""
    s = skill.lower().strip()
    if not s:
        return 0
    score = 0
    for k in job_keywords:
        if k in s or s in k:
            score += 1
    return score


def select_skills_for_job(
    skills: dict[str, Any] | list[Any],
    job_keywords: list[str],
    max_items: int = 20,
) -> list[str]:
    """Select and rank skills by relevance to job. Returns top skill strings."""
    flat = _flatten_skills(skills)
    keywords = _normalize_keywords(job_keywords)
    scored = [(score_skill(s, keywords), s) for s in flat]
    scored.sort(key=lambda x: (-x[0], x[1]))
    seen: set[str] = set()
    out: list[str] = []
    for _, s in scored[: max_items * 2]:
        if s.lower() in seen:
            continue
        seen.add(s.lower())
        out.append(s)
        if len(out) >= max_items:
            break
    return out


def _esc_line(s: str) -> str:
    s = (s or "").strip()
    return s.replace("\n", " ")


def _projects_section_markdown(projects: list[dict]) -> str:
    """Build markdown Projects section from selected projects (name, dates, tech_stack, description, bullets)."""
    lines: list[str] = []
    if not projects:
        return ""
    lines.append("")
    lines.append("## Projects")
    for p in projects:
        name = _esc_line(str(p.get("name") or ""))
        if not name:
            continue
        lines.append("")
        lines.append(f"**{name}**")
        dates = _esc_line(str(p.get("dates") or ""))
        if dates:
            lines.append(dates)
        tech = p.get("tech_stack") or []
        desc = _esc_line(str(p.get("description") or ""))
        if isinstance(tech, list) and tech:
            tech_str = ", ".join(_esc_line(str(t)) for t in tech if t)
            if tech_str:
                lines.append("")
                if desc:
                    lines.append(f"{tech_str}. {desc}")
                else:
                    lines.append(tech_str)
        elif desc:
            lines.append("")
            lines.append(desc)
        for b in p.get("bullets") or []:
            bt = _esc_line(str(b))
            if bt:
                lines.append(f"- {bt}")
    return "\n".join(lines)


def generate_artifacts_heuristic(
    job_slug: str,
    job_json: dict,
    tone: str,
    focus: str,
    length: str,
    user_id: str | None = None,
    db: "Session | None" = None,
) -> tuple[str, str, str]:
    """Generate resume, cover, notes without LLM: match projects/skills to job, assemble from profile. Same return shape as generate_artifacts."""
    if user_id is not None and db is not None:
        resume_base = get_resume_base_db(user_id, db)
        profile = get_profile(user_id, db)
        skills = get_skills(user_id, db)
        selected_projects = select_projects(job_json.get("keywords") or [], length, user_id, db)
    else:
        from app.services.truth_store import get_resume_base as get_resume_base_yaml
        resume_base = get_resume_base_yaml()
        profile = get_profile("", None)
        skills = get_skills()
        selected_projects = select_projects(job_json.get("keywords") or [], length)
    keywords = job_json.get("keywords") or []
    selected_skills = select_skills_for_job(skills, keywords, max_items=20)

    # Resume: base markdown + Projects section
    resume_md = resume_base_to_markdown(resume_base)
    projects_md = _projects_section_markdown(selected_projects)
    if projects_md:
        resume_md = resume_md.rstrip() + "\n" + projects_md
    if selected_skills:
        resume_md = resume_md.rstrip() + "\n\n## Skills emphasized for this role\n\n" + ", ".join(selected_skills[:15]) + "\n"

    # Cover: template from profile + job only
    contact = profile.get("contact") if isinstance(profile.get("contact"), dict) else {}
    name = (contact.get("name") or profile.get("name") or "").strip() or "Candidate"
    company = (job_json.get("company") or "").strip() or "the company"
    role = (job_json.get("role") or "").strip() or "the role"
    pitch = (profile.get("pitch") or "").strip()
    cover_lines = [
        f"# Cover letter — {role} at {company}",
        "",
        f"Dear Hiring Manager,",
        "",
        f"I am writing to apply for the {role} position at {company}.",
        "",
    ]
    if pitch:
        cover_lines.append(pitch[:800])
        cover_lines.append("")
    cover_lines.extend([
        "Please review my attached resume. I look forward to discussing how my experience aligns with your needs.",
        "",
        "Sincerely,",
        "",
        name,
    ])
    cover_md = "\n".join(cover_lines)

    # Notes: keywords, selected projects/skills, next steps
    notes_lines = [
        "# Notes for this application",
        "",
        "## Keywords to emphasize",
        "",
    ]
    for k in keywords[:25]:
        notes_lines.append(f"- {k}")
    notes_lines.extend(["", "## Projects matched for this role", ""])
    for p in selected_projects:
        notes_lines.append(f"- {p.get('name') or 'Project'}")
    if selected_skills:
        notes_lines.extend(["", "## Skills aligned with posting", ""])
        notes_lines.append(", ".join(selected_skills[:15]))
    notes_lines.extend([
        "",
        "## Next steps",
        "",
        "- Edit your resume and cover letter above before sending.",
        "- Use these keywords and projects as talking points in interviews.",
    ])
    notes_md = "\n".join(notes_lines)

    return resume_md, cover_md, notes_md


# ---------------------------------------------------------------------------
# Exemplar selection: classify the JD, then inject reference exemplars (form only)
# ---------------------------------------------------------------------------

# Lowercase substrings mapped to a role_family; counted across role + keywords + description.
_FAMILY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("ai_llm", ("llm", "genai", "generative ai", "prompt engineer", "rag", "openai",
                "anthropic", "chatbot", "gpt", "agentic", "ai governance")),
    ("data_ml", ("machine learning", " ml ", "data scien", "tensorflow", "pytorch",
                 "analytics", "data strateg", "etl", "dashboard", "data engineer",
                 "data governance", "data pipeline")),
    ("devops_sre", ("devops", "sre", "site reliability", "ci/cd", "kubernetes",
                    "terraform", "ansible", "observability", "incident")),
    ("platform", ("platform engineer", "internal tooling", "developer experience",
                  "developer platform", "platform team")),
    ("infra", ("infrastructure", "cloud engineer", "system administ", "networking",
               "data center", "virtualization")),
    ("backend", ("backend", "back-end", "back end", "api develop", "microservice",
                 "fastapi", "django", "node.js", "server-side")),
]

_SENIOR_RE = re.compile(r"\b(senior|sr\.?|lead|principal|staff|head of|director)\b", re.I)
_JUNIOR_RE = re.compile(r"\b(junior|jr\.?|entry[- ]level|intern|associate|graduate)\b", re.I)


def _heuristic_family(role: str, keywords: list[str], desc: str) -> str:
    hay = " ".join([role or "", " ".join(str(k) for k in (keywords or [])), desc or ""]).lower()
    best_family = "other"
    best_hits = 0
    for family, terms in _FAMILY_KEYWORDS:
        hits = sum(1 for t in terms if t in hay)
        if hits > best_hits:
            best_hits = hits
            best_family = family
    return best_family


def _heuristic_seniority(role: str, desc: str) -> str:
    if _JUNIOR_RE.search(role or ""):
        return "mid"
    if _SENIOR_RE.search(f"{role or ''}\n{desc or ''}"):
        return "senior"
    return "mid"


def _heuristic_tags(keywords: list[str], limit: int = 10) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for k in keywords or []:
        s = str(k).strip().lower()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
        if len(out) >= limit:
            break
    return out


def _parse_json_obj(raw: str) -> dict:
    """Parse a JSON object from an LLM response, tolerating code fences and surrounding prose."""
    s = (raw or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s).strip()
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        s = s[start : end + 1]
    data = json.loads(s)
    return data if isinstance(data, dict) else {}


def classify_job_for_exemplars(job_json: dict, _chat=None) -> dict:
    """Return {role_family, seniority, tags} for a JD. Uses the LLM when _chat is given, else heuristics.

    The heuristic path always runs as the fallback for any field the LLM omits or returns invalid,
    so selection works (and degrades gracefully) with or without an API key.
    """
    role = (job_json.get("role") or "").strip()
    desc = (job_json.get("raw_body") or "")[:4000]
    keywords = job_json.get("keywords") or []

    fallback = {
        "role_family": _heuristic_family(role, keywords, desc),
        "seniority": _heuristic_seniority(role, desc),
        "tags": _heuristic_tags(keywords),
    }
    if _chat is None:
        return fallback

    system = "You classify a job description to select writing examples. Respond with ONLY a JSON object, no prose."
    user = (
        "Classify this job. Return a JSON object with exactly these keys:\n"
        f'  "role_family": one of {list(ROLE_FAMILIES)}\n'
        '  "seniority": one of ["mid", "senior"]\n'
        '  "tags": array of 3-8 short lowercase kebab-case topic tags (skills/themes)\n\n'
        f"Role: {role}\n\nDescription:\n{desc}"
    )
    try:
        raw = _chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0,
        )
        data = _parse_json_obj(raw)
    except Exception:
        return fallback

    rf = str(data.get("role_family") or "").strip().lower()
    if rf not in ROLE_FAMILIES:
        rf = fallback["role_family"]
    sen = str(data.get("seniority") or "").strip().lower()
    if sen not in ("mid", "senior"):
        sen = fallback["seniority"]
    tags = [str(t).strip().lower() for t in (data.get("tags") or []) if str(t).strip()][:8]
    if not tags:
        tags = fallback["tags"]
    return {"role_family": rf, "seniority": sen, "tags": tags}


# Verbatim instruction block. Keep exactly as specified: it teaches form, forbids copying content.
_EXEMPLAR_BLOCK_HEADER = """REFERENCE EXEMPLARS
The documents below are human-approved, high-quality tailored applications for
OTHER roles. Use them ONLY as demonstrations of form: section order and
headings, bullet structure and density, sentence voice and tone, length,
formatting conventions (no em dashes; plain hyphens for ranges), and how to
acknowledge skill gaps honestly and confidently.

Do NOT copy any content from the exemplars: no employers, project names,
metrics, phrasing, or skill claims. Every fact in the output must come solely
from the candidate's truth stores and the target job description. If an
exemplar references a tool or experience the truth stores do not contain, do
not carry it over.

Match the exemplars' voice and structure; source all substance from the
truth stores."""


def _build_exemplar_block(exemplars: list[dict]) -> str:
    """Render the verbatim REFERENCE EXEMPLARS block plus each wrapped exemplar.

    Returns "" when the list is empty so callers can append unconditionally and degrade to
    current behaviour when no exemplar matches.
    """
    if not exemplars:
        return ""
    parts = [_EXEMPLAR_BLOCK_HEADER]
    for ex in exemplars:
        doc_type = (ex.get("doc_type") or "").strip()
        target_role = (ex.get("target_role") or "").strip()
        jd_summary = (ex.get("jd_summary") or "").strip()
        body = (ex.get("body") or "").strip()
        parts.append(
            f'<exemplar doc_type="{doc_type}" target_role="{target_role}">\n'
            f"JD it was tailored to: {jd_summary}\n"
            "---\n"
            f"{body}\n"
            "</exemplar>"
        )
    return "\n\n".join(parts)


def generate_artifacts(
    job_slug: str,
    job_json: dict,
    tone: str,
    focus: str,
    length: str,
    model: str | None = None,
    user_id: str | None = None,
    db: "Session | None" = None,
) -> tuple[str, str, str]:
    """Generate resume.md, cover_letter.md, notes.md content. When user has no LLM API key, uses heuristic (match + assemble); otherwise LLM. Returns (resume_md, cover_letter_md, notes_md)."""
    if user_id is not None and db is not None:
        resume_base = get_resume_base_db(user_id, db)
        profile = get_profile(user_id, db)
        skills = get_skills(user_id, db)
        selected = select_projects(job_json.get("keywords") or [], length, user_id, db)
    else:
        from app.services.truth_store import get_resume_base as get_resume_base_yaml
        resume_base = get_resume_base_yaml()
        profile = get_profile("", None)  # legacy: no user_id yields YAML profile or default
        skills = get_skills()
        selected = select_projects(job_json.get("keywords") or [], length)

    # No user API key → heuristic only (do not use server LLM_API_KEY for this user)
    if not (profile.get("llm_api_key") or "").strip():
        return generate_artifacts_heuristic(
            job_slug, job_json, tone, focus, length, user_id=user_id, db=db
        )

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
When a "profile" object is provided, use its name, email, phone, linkedin, website, github for contact and any "pitch" text where appropriate in the cover letter.
When an "ats" object is provided, use it to improve ATS (applicant tracking system) match: mirror the listed action_verbs in bullet points where accurate, weave in key_phrases from the job where they fit your real experience, and align wording with education/years_experience when true. Do not lie; only use ATS signals that genuinely apply to the candidate's background."""

    # LLM overrides: from profile when user has set an API key, else env; request model overrides when set
    llm_kwargs: dict = {}
    if profile.get("llm_api_key"):
        llm_kwargs["provider"] = profile.get("llm_provider") or "openrouter"
        llm_kwargs["api_key"] = profile["llm_api_key"]
        llm_kwargs["model"] = (model or profile.get("llm_model") or "").strip() or profile.get("llm_model")
        llm_kwargs["temperature"] = profile.get("llm_temperature")
    else:
        if model:
            llm_kwargs["model"] = model

    def _chat(msgs: list, **kwargs: object) -> str:
        return chat_completion(msgs, **{**llm_kwargs, **kwargs})

    # Reference exemplars (form only): classify this JD, then select matching human-approved docs.
    # Gated on a non-empty library so empty/no-match degrades to current behaviour with no extra calls.
    resume_exemplar_block = ""
    cover_exemplar_block = ""
    if exemplar_store.get_exemplars():
        meta = classify_job_for_exemplars(job_json, _chat=_chat)
        resume_exemplar_block = _build_exemplar_block(
            exemplar_store.select_exemplars(
                meta["role_family"], meta["seniority"], meta["tags"], "resume", k=1, max_k=2
            )
        )
        cover_exemplar_block = _build_exemplar_block(
            exemplar_store.select_exemplars(
                meta["role_family"], meta["seniority"], meta["tags"], "cover_letter", k=1, max_k=2
            )
        )

    resume_format = """
Resume formatting rules (follow exactly):
- Contact header: Put name and title at top. Then list email and phone as plain text on one line. For LinkedIn, website, and GitHub use markdown links only: write [LinkedIn](url), [Website](url), [GitHub](url) so the PDF shows the label as a clickable hyperlink, not the raw URL. Do not paste full URLs as visible text; use hyperlinked labels only.
- Work experience: For each role use a short line that does not wrap. Put job title first. Use "CFB Wainwright" instead of "Canadian Forces Base Wainwright". Put location on the same line as the title after a separator (e.g. "|") or on the next line if the line would be too long. Keep the date range (e.g. 2020 – 2022) on the same line as the title or with the location.
- Projects: For each project use this structure with explicit line breaks:
  **Project Name**
  Timeframe (e.g. 2025–present)

  Tech stack and description paragraph (blank line after timeframe, blank line before this paragraph).
"""

    # Resume
    resume_prompt = f"""Using ONLY the data below, write a tailored resume in markdown for this job. Tone: {tone}. Focus: {focus}. Length: {length}. No invented facts. Use the "ats" signals (action_verbs, key_phrases) to phrase bullets so they match the job description where accurate.
{resume_format}

{context_str}"""
    # Exemplars go AFTER the truth JSON, clearly delimited, so the model never confuses example
    # form with the candidate's real facts.
    if resume_exemplar_block:
        resume_prompt = f"{resume_prompt}\n\n{resume_exemplar_block}"
    resume_md = _chat(
        [{"role": "system", "content": system}, {"role": "user", "content": resume_prompt}],
    )

    # Cover letter
    cover_prompt = f"""Using ONLY the data below, write a short cover letter in markdown for this role at this company. Tone: {tone}. No invented facts. Where relevant, use the "ats" action_verbs and key_phrases to echo the job language.\n\n{context_str}"""
    if cover_exemplar_block:
        cover_prompt = f"{cover_prompt}\n\n{cover_exemplar_block}"
    cover_md = _chat(
        [{"role": "system", "content": system}, {"role": "user", "content": cover_prompt}],
    )

    # Notes
    notes_prompt = f"""Given the job and the resume data, output a brief markdown notes document with: 1) Keywords to emphasize, 2) Interview prep talking points, 3) Gaps/risks to address. Use only info from the context.\n\n{context_str}"""
    notes_md = _chat(
        [{"role": "system", "content": system}, {"role": "user", "content": notes_prompt}],
    )

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
