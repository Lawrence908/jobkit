"""Supabase Storage for job artifacts: job.json, job.md, generated MDs, PDFs."""
import json
import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

BUCKET = "jobkit-artifacts"


def use_storage() -> bool:
    """True when Supabase URL and service role key are set (Storage available)."""
    s = get_settings()
    return bool(s.supabase_url and s.supabase_url.strip() and s.supabase_service_role_key and s.supabase_service_role_key.strip())


def _client():
    """Supabase client with service role (for Storage)."""
    from supabase import create_client
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_service_role_key)


_bucket_warning_logged = False


def _ensure_bucket():
    """Ensure bucket exists (create if not). Idempotent."""
    global _bucket_warning_logged
    try:
        client = _client()
        buckets = client.storage.list_buckets()
        names = [b.name for b in (buckets or [])]
        if BUCKET not in names:
            client.storage.create_bucket(BUCKET, options={"private": True})
            logger.info("Created storage bucket %s", BUCKET)
    except ImportError as e:
        if not _bucket_warning_logged:
            _bucket_warning_logged = True
            logger.warning("Supabase storage unavailable (install supabase package): %s", e)
    except Exception as e:
        if not _bucket_warning_logged:
            _bucket_warning_logged = True
            logger.warning("Could not ensure bucket %s: %s", BUCKET, e)


# Path conventions (storage keys, no leading slash)
def job_json_key(user_id: str, slug: str) -> str:
    return f"{user_id}/jobs/{slug}/job.json"


def job_md_key(user_id: str, slug: str) -> str:
    return f"{user_id}/jobs/{slug}/job.md"


def generated_key(user_id: str, slug: str, filename: str) -> str:
    return f"{user_id}/jobs/{slug}/generated/{filename}"


def output_pdf_key(user_id: str, slug: str, filename: str) -> str:
    """PDFs live under the same job folder as generated MDs: user_id/jobs/slug/generated/."""
    return generated_key(user_id, slug, filename)


def is_storage_key(path: str) -> bool:
    """True if path looks like a storage key (user_id/jobs/... or legacy user_id/outputs/...)."""
    if not path or "/" not in path:
        return False
    first = path.split("/")[0]
    # UUID-like: 8-4-4-4-12 hex chars
    if len(first) != 36:
        return False
    return first.replace("-", "").isalnum() and path.startswith((first + "/jobs/", first + "/outputs/"))


def upload_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """Upload bytes to Storage at key. Overwrites if exists."""
    _ensure_bucket()
    client = _client()
    file_options = {"content-type": content_type, "upsert": "true"}
    client.storage.from_(BUCKET).upload(key, data, file_options)


def download_bytes(key: str) -> bytes:
    """Download object at key; raises if not found."""
    client = _client()
    return client.storage.from_(BUCKET).download(key)


def create_signed_url(key: str, expires_in: int = 3600) -> str:
    """Create a signed URL for download (e.g. redirect in download endpoint)."""
    client = _client()
    res = client.storage.from_(BUCKET).create_signed_url(key, expires_in)
    if isinstance(res, dict) and "signedURL" in res:
        return res["signedURL"]
    if hasattr(res, "signed_url"):
        return res.signed_url
    if hasattr(res, "signedURL"):
        return res.signedURL
    raise ValueError("Unexpected signed URL response")


def upload_job_files(user_id: str, slug: str, job_json: dict[str, Any], job_md: str) -> None:
    """Write job.json and job.md to Storage for this user/slug."""
    upload_bytes(job_json_key(user_id, slug), json.dumps(job_json, indent=2).encode("utf-8"), "application/json")
    upload_bytes(job_md_key(user_id, slug), job_md.encode("utf-8"), "text/markdown")


def download_job_json(user_id: str, slug: str) -> dict[str, Any]:
    """Load job.json from Storage."""
    raw = download_bytes(job_json_key(user_id, slug))
    return json.loads(raw.decode("utf-8"))


def download_job_md(user_id: str, slug: str) -> str:
    """Load job.md from Storage."""
    return download_bytes(job_md_key(user_id, slug)).decode("utf-8")


def upload_generated_mds(user_id: str, slug: str, resume_md: str, cover_md: str, notes_md: str) -> list[tuple[str, str]]:
    """Upload resume.md, cover_letter.md, notes.md to Storage. Returns [(art_type, storage_key), ...]."""
    pairs = [
        ("resume_md", "resume.md", resume_md),
        ("cover_letter_md", "cover_letter.md", cover_md),
        ("notes_md", "notes.md", notes_md),
    ]
    for art_type, name, content in pairs:
        upload_bytes(generated_key(user_id, slug, name), content.encode("utf-8"), "text/markdown")
    return [(art_type, generated_key(user_id, slug, name)) for art_type, name, _ in pairs]


def download_generated_md(user_id: str, slug: str, filename: str) -> str:
    """Download one generated file (e.g. resume.md) from Storage."""
    return download_bytes(generated_key(user_id, slug, filename)).decode("utf-8")


def has_generated_content(user_id: str, slug: str) -> bool:
    """True if generated content (e.g. resume.md) exists in Storage for this job."""
    try:
        download_bytes(generated_key(user_id, slug, "resume.md"))
        return True
    except Exception:
        return False


def upload_output_pdf(user_id: str, slug: str, filename: str, pdf_bytes: bytes) -> str:
    """Upload a PDF to job folder (user_id/jobs/slug/generated/); returns storage key."""
    key = output_pdf_key(user_id, slug, filename)
    upload_bytes(key, pdf_bytes, "application/pdf")
    return key


def generated_artifact_paths(user_id: str, slug: str) -> list[tuple[str, str]]:
    """Return [(art_type, storage_key), ...] for the three generated MDs."""
    return [
        ("resume_md", generated_key(user_id, slug, "resume.md")),
        ("cover_letter_md", generated_key(user_id, slug, "cover_letter.md")),
        ("notes_md", generated_key(user_id, slug, "notes.md")),
    ]
