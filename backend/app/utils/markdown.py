"""Markdown helpers."""
import re


def escape_for_markdown(s: str) -> str:
    """Escape characters that could break markdown."""
    if not s:
        return ""
    return re.sub(r"([*_`\[\]#])", r"\\\1", s)
