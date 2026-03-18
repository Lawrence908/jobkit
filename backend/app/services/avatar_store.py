"""Per-user profile avatar on disk (optional). Not embedded in generated resume PDFs unless added separately."""
from __future__ import annotations

import io
import re
from pathlib import Path

from PIL import Image

from app.core.config import get_settings

_MAX_UPLOAD_BYTES = 2 * 1024 * 1024
_MAX_EDGE = 512


def _safe_user_segment(user_id: str) -> str:
    s = re.sub(r"[^0-9a-fA-F-]", "", user_id.strip())
    return s[:128] if s else "user"


def avatar_path(user_id: str) -> Path:
    settings = get_settings()
    return settings.jobkit_data_dir / "avatars" / f"{_safe_user_segment(user_id)}.jpg"


def has_avatar(user_id: str) -> bool:
    return avatar_path(user_id).is_file()


def read_avatar_bytes(user_id: str) -> bytes | None:
    path = avatar_path(user_id)
    if not path.is_file():
        return None
    try:
        return path.read_bytes()
    except OSError:
        return None


def delete_avatar(user_id: str) -> None:
    path = avatar_path(user_id)
    if path.is_file():
        try:
            path.unlink()
        except OSError:
            pass


def save_avatar_from_upload(user_id: str, raw: bytes) -> None:
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise ValueError("Image too large (max 2MB)")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as e:
        raise ValueError("Not a valid image") from e
    if img.width * img.height > 25_000_000:
        raise ValueError("Image dimensions too large")
    img.thumbnail((_MAX_EDGE, _MAX_EDGE), Image.Resampling.LANCZOS)
    if img.mode != "RGB":
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[3])
        img = bg
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88, optimize=True)
    out = buf.getvalue()
    path = avatar_path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out)
