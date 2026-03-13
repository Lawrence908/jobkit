"""Load and save personalization profile (contact, pitch, defaults) from YAML."""
import logging
from pathlib import Path
from typing import Any

import yaml

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_DEFAULT_PROFILE: dict[str, Any] = {
    "name": "",
    "email": "",
    "phone": "",
    "linkedin": "",
    "website": "",
    "github": "",
    "pitch": "",
    "default_tone": "neutral",
    "default_focus": "full-stack",
    "default_length": "1 page",
}


def _profile_path() -> Path:
    return get_settings().jobkit_data_dir / "profile.yml"


def get_profile() -> dict[str, Any]:
    """Load profile from profile.yml; return default dict if missing or invalid."""
    path = _profile_path()
    if not path.exists():
        return _DEFAULT_PROFILE.copy()
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        out = _DEFAULT_PROFILE.copy()
        for k in out:
            if k in data and data[k] is not None:
                out[k] = data[k]
        return out
    except Exception as e:
        logger.warning("Failed to load profile %s: %s", path, e)
        return _DEFAULT_PROFILE.copy()


def save_profile(profile: dict[str, Any]) -> None:
    """Write profile to profile.yml (only known keys)."""
    path = _profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {k: profile.get(k, _DEFAULT_PROFILE[k]) for k in _DEFAULT_PROFILE}
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
