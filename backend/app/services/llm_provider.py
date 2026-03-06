"""OpenAI-compatible LLM client."""
import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def chat_completion(messages: list[dict[str, str]], temperature: float | None = None) -> str:
    """Call OpenAI-compatible chat completion; return content of first choice."""
    settings = get_settings()
    url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": temperature if temperature is not None else settings.llm_temperature,
    }
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("No choices in LLM response")
    content = choices[0].get("message", {}).get("content") or ""
    return content.strip()
