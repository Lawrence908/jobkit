"""Curated few-shot exemplar library: human-approved tailored docs loaded from disk.

Mirrors truth_store.py: a global, disk-backed, startup-loaded cache. Exemplars teach the
LLM the target FORM (section order, bullet density, voice, length, formatting, honest gap
handling) without ever copying their content. This is a config library like resume_base.yml
and skills.yml, so it is disk-only even in Supabase mode (read from JOBKIT_DATA_DIR/exemplars).

A single shared library across users: only the document form is shared, never content. If
per-user scoping is wanted later, nest files under exemplars/{user_id}/.
"""
import hashlib
import logging
import re
import time
from pathlib import Path
from typing import Any

import yaml

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Allowed role_family values (single source of truth; imported by tailor.py).
ROLE_FAMILIES: tuple[str, ...] = (
    "devops_sre",
    "platform",
    "data_ml",
    "ai_llm",
    "backend",
    "infra",
    "other",
)

# Broader family groups: an exemplar in the same group as the JD scores a partial role match
# and is a valid "nearest role_family" fallback when nothing scores positively.
FAMILY_GROUPS: dict[str, str] = {
    "devops_sre": "infra",
    "platform": "infra",
    "infra": "infra",
    "data_ml": "data_ai",
    "ai_llm": "data_ai",
    "backend": "backend",
    "other": "other",
}

DOC_TYPES: tuple[str, ...] = ("resume", "cover_letter")

# Frontmatter keys carried on every record (plus body). All 9 are present on the seeds.
_RECORD_KEYS: tuple[str, ...] = (
    "id",
    "doc_type",
    "role_family",
    "seniority",
    "target_role",
    "jd_summary",
    "tags",
    "quality_notes",
    "body",
)

_exemplars: list[dict[str, Any]] = []
_loaded_at: float | None = None


def _exemplars_dir() -> Path:
    return get_settings().jobkit_data_dir / "exemplars"


def _load_yaml(path: Path) -> dict[str, Any] | None:
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else None
    except Exception as e:
        logger.warning("Failed to load exemplar %s: %s", path, e)
        return None


def _normalize_record(data: dict[str, Any], path: Path) -> dict[str, Any]:
    """Coerce a parsed YAML mapping into a normalized exemplar record with all keys present."""
    tags = data.get("tags")
    if isinstance(tags, str):
        tags = [tags]
    tags = [str(t).strip().lower() for t in (tags or []) if str(t).strip()]
    return {
        "id": (str(data.get("id") or "").strip() or path.stem),
        "doc_type": (str(data.get("doc_type") or "").strip().lower()),
        "role_family": (str(data.get("role_family") or "other").strip().lower()),
        "seniority": (str(data.get("seniority") or "").strip().lower()),
        "target_role": (str(data.get("target_role") or "").strip()),
        "jd_summary": (str(data.get("jd_summary") or "").strip()),
        "tags": tags,
        "quality_notes": (str(data.get("quality_notes") or "").strip()),
        "body": (str(data.get("body") or "")).strip(),
    }


def load_exemplars() -> None:
    """Load every JOBKIT_DATA_DIR/exemplars/*.yml into the in-memory cache. Idempotent."""
    global _exemplars, _loaded_at
    ex_dir = _exemplars_dir()
    records: list[dict[str, Any]] = []
    if ex_dir.is_dir():
        for f in sorted(ex_dir.glob("*.yml")):
            data = _load_yaml(f)
            if not isinstance(data, dict):
                continue
            if not data.get("body") or not data.get("doc_type"):
                logger.warning("Skipping exemplar %s: missing body or doc_type", f.name)
                continue
            records.append(_normalize_record(data, f))
    _exemplars = records
    _loaded_at = time.time()
    logger.info("Exemplar store loaded: %d exemplars", len(records))


def get_exemplars() -> list[dict[str, Any]]:
    return _exemplars


def get_loaded_at() -> float | None:
    return _loaded_at


def score_exemplar(
    record: dict[str, Any],
    role_family: str,
    seniority: str,
    tags: list[str],
) -> int:
    """Score one exemplar against JD metadata: tag overlap x2, exact role +3 (same group +1), seniority +1."""
    score = 0
    rec_tags = {str(t).lower() for t in (record.get("tags") or [])}
    want_tags = {str(t).lower() for t in (tags or [])}
    score += 2 * len(rec_tags & want_tags)

    rf = (record.get("role_family") or "").strip().lower()
    want_rf = (role_family or "").strip().lower()
    if rf and want_rf:
        if rf == want_rf:
            score += 3
        elif FAMILY_GROUPS.get(rf) and FAMILY_GROUPS.get(rf) == FAMILY_GROUPS.get(want_rf):
            score += 1

    rec_sen = (record.get("seniority") or "").strip().lower()
    want_sen = (seniority or "").strip().lower()
    if rec_sen and want_sen and rec_sen == want_sen:
        score += 1
    return score


def select_exemplars(
    role_family: str,
    seniority: str,
    tags: list[str],
    doc_type: str,
    k: int = 1,
    max_k: int = 2,
) -> list[dict[str, Any]]:
    """Top-K exemplars for a doc_type by score. Falls back to nearest role_family; [] when no match.

    Hard cap of 2 regardless of k/max_k so the prompt never carries more than two examples.
    """
    want_doc = (doc_type or "").strip().lower()
    pool = [r for r in _exemplars if (r.get("doc_type") or "").strip().lower() == want_doc]
    if not pool:
        return []
    cap = min(2, max(1, min(k if k else 1, max_k)))
    scored = sorted(
        ((score_exemplar(r, role_family, seniority, tags), r) for r in pool),
        key=lambda x: -x[0],
    )
    positive = [r for s, r in scored if s > 0]
    if positive:
        return positive[:cap]
    # No positive score: fall back to nearest role_family (same broad family group).
    want_group = FAMILY_GROUPS.get((role_family or "").strip().lower())
    if want_group:
        near = [
            r
            for _, r in scored
            if FAMILY_GROUPS.get((r.get("role_family") or "").strip().lower()) == want_group
        ]
        if near:
            return near[:cap]
    return []


# ---------------------------------------------------------------------------
# Writing (promote path)
# ---------------------------------------------------------------------------

class _LiteralDumper(yaml.SafeDumper):
    """YAML dumper that emits multi-line strings as literal block scalars (matches the seeds)."""


def _str_representer(dumper: yaml.SafeDumper, data: str):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_LiteralDumper.add_representer(str, _str_representer)


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return s or "exemplar"


def build_exemplar_id(target_role: str, doc_type: str, body: str) -> str:
    """Stable id from slugified target_role + doc_type + a short body hash (collision-resistant)."""
    base = f"{_slugify(target_role)}-{_slugify(doc_type)}"
    digest = hashlib.sha1((body or "").encode("utf-8")).hexdigest()[:8]
    return f"{base}-{digest}"


def write_exemplar(record: dict[str, Any]) -> Path:
    """Write exemplars/{id}.yml with full frontmatter + body, then reload the library. Returns the path."""
    ex_dir = _exemplars_dir()
    ex_dir.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_record(record, ex_dir / "new.yml")
    if not normalized["id"] or normalized["id"] == "new":
        normalized["id"] = build_exemplar_id(
            normalized["target_role"], normalized["doc_type"], normalized["body"]
        )
    # Stable, human-friendly key order matching the seed files.
    ordered = {k: normalized[k] for k in _RECORD_KEYS}
    path = ex_dir / f"{normalized['id']}.yml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            ordered,
            f,
            Dumper=_LiteralDumper,
            sort_keys=False,
            allow_unicode=True,
            width=4096,
            default_flow_style=False,
        )
    load_exemplars()
    return path
