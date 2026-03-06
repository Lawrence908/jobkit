"""Job ingestion: URL fetch, readability, markdown export, disk storage."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from readability import Document

from app.core.config import get_settings
from app.services.extract import extract_keywords, extract_ats_signals, merge_extracted
from app.utils.files import job_slug, ensure_safe_relative_path

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; JobKit/1.0)"


def fetch_and_parse(url: str) -> tuple[str, str, str]:
    """Fetch URL, parse with readability. Returns (title, body_html, body_text)."""
    with httpx.Client(follow_redirects=True, timeout=15.0, headers={"User-Agent": USER_AGENT}) as client:
        resp = client.get(url)
        resp.raise_for_status()
        html = resp.text
    doc = Document(html)
    title = doc.title() or ""
    body_html = doc.summary()
    # Strip tags for plain text
    import re
    body_text = re.sub(r"<[^>]+>", " ", body_html)
    body_text = re.sub(r"\s+", " ", body_text).strip()
    return title, body_html, body_text


def url_to_job_json(url: str, raw_text: str | None = None) -> dict[str, Any]:
    """Produce job_json from URL (and optional raw_text fallback)."""
    job_json: dict[str, Any] = {
        "url": url,
        "company": "",
        "role": "",
        "location": "",
        "source": "url",
        "keywords": [],
    }
    title = ""
    body = ""
    try:
        title, _body_html, body = fetch_and_parse(url)
        job_json["raw_body"] = body
    except Exception as e:
        logger.warning("Fetch failed for %s: %s", url[:80], e)
        if raw_text:
            body = raw_text
            job_json["raw_body"] = raw_text
            job_json["source"] = "paste"
        else:
            raise ValueError("Could not fetch URL; provide raw job description text") from e
    if raw_text and not body.strip():
        body = raw_text
        job_json["raw_body"] = raw_text
        job_json["source"] = "paste"
    merge_extracted(job_json, title, body)
    return job_json


def paste_only_to_job_json(raw_text: str) -> dict[str, Any]:
    """Produce job_json from pasted text only."""
    job_json: dict[str, Any] = {
        "url": None,
        "company": "",
        "role": "",
        "location": "",
        "source": "paste",
        "raw_body": raw_text,
        "keywords": extract_keywords(raw_text),
        "ats": extract_ats_signals(raw_text),
    }
    return job_json


def job_json_to_markdown(job_json: dict[str, Any]) -> str:
    """Turn job_json into a canonical job.md string."""
    lines = []
    if job_json.get("role"):
        lines.append(f"# {job_json['role']}")
    if job_json.get("company"):
        lines.append(f"**Company:** {job_json['company']}")
    if job_json.get("location"):
        lines.append(f"**Location:** {job_json['location']}")
    if job_json.get("url"):
        lines.append(f"**URL:** {job_json['url']}")
    lines.append("")
    lines.append("## Description")
    lines.append("")
    lines.append(job_json.get("raw_body", ""))
    if job_json.get("keywords"):
        lines.append("")
        lines.append("## Keywords")
        lines.append(", ".join(job_json["keywords"]))
    ats = job_json.get("ats") or {}
    if ats.get("action_verbs") or ats.get("education") or ats.get("key_phrases"):
        lines.append("")
        lines.append("## ATS signals")
        if ats.get("action_verbs"):
            lines.append("- **Action verbs:** " + ", ".join(ats["action_verbs"]))
        if ats.get("years_experience"):
            lines.append(f"- **Years experience:** {ats['years_experience']}")
        if ats.get("education"):
            lines.append("- **Education:** " + "; ".join(ats["education"]))
        if ats.get("key_phrases"):
            lines.append("- **Key phrases:** " + "; ".join(ats["key_phrases"][:10]))
    return "\n".join(lines)


def save_job_to_disk(slug: str, job_json: dict[str, Any], job_md: str) -> Path:
    """Write job.md and job.json under JOBKIT_JOBS_DIR/<slug>/."""
    settings = get_settings()
    base = ensure_safe_relative_path(settings.jobkit_jobs_dir, slug)
    base.mkdir(parents=True, exist_ok=True)
    (base / "job.json").write_text(json.dumps(job_json, indent=2), encoding="utf-8")
    (base / "job.md").write_text(job_md, encoding="utf-8")
    return base


def ingest_job(url: str | None, raw_text: str | None) -> dict[str, Any]:
    """
    Ingest a job from URL and/or pasted text.
    Returns job_json (with slug set) and writes job.md + job.json to disk.
    """
    if url and url.strip():
        job_json = url_to_job_json(url.strip(), raw_text)
    elif raw_text and raw_text.strip():
        job_json = paste_only_to_job_json(raw_text.strip())
    else:
        raise ValueError("Provide either job URL or raw job description text")
    # Slug from company, role, today
    slug = job_slug(
        job_json.get("company") or "company",
        job_json.get("role") or "role",
        datetime.utcnow(),
    )
    job_json["slug"] = slug
    job_md = job_json_to_markdown(job_json)
    save_job_to_disk(slug, job_json, job_md)
    return job_json
