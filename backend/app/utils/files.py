"""Path safety and slug generation."""
import re
from datetime import datetime
from pathlib import Path


def sanitize_slug_part(s: str, max_len: int = 80) -> str:
    """Make a string safe for use in a path slug: alphanumeric, hyphens, underscores only."""
    if not s or not s.strip():
        return "unknown"
    s = s.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s)
    s = s.strip("-") or "unknown"
    return s[:max_len]


def job_slug(company: str, role: str, date: datetime | None = None) -> str:
    """Generate slug: <company>-<role>-<yyyy-mm-dd>. Path-safe."""
    company_part = sanitize_slug_part(company or "company", 60)
    role_part = sanitize_slug_part(role or "role", 60)
    if date is None:
        date = datetime.utcnow()
    date_part = date.strftime("%Y-%m-%d")
    return f"{company_part}-{role_part}-{date_part}"


def ensure_safe_relative_path(base: Path, *parts: str) -> Path:
    """Build a path under base; raise if result is not under base (path traversal)."""
    resolved = (base / "/".join(parts)).resolve()
    base_resolved = base.resolve()
    if not str(resolved).startswith(str(base_resolved)):
        raise ValueError("Path traversal not allowed")
    return resolved
