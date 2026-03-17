"""OpenAI-compatible and Anthropic LLM client. Supports profile overrides (base_url, api_key, model, temperature)."""
import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Provider slug -> (base_url, use_anthropic_messages_api)
PROVIDER_CONFIG: dict[str, tuple[str, bool]] = {
    "openrouter": ("https://openrouter.ai/api/v1", False),
    "openai": ("https://api.openai.com/v1", False),
    "anthropic": ("https://api.anthropic.com", True),
}


def _anthropic_messages(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float,
) -> str:
    """Call Anthropic Messages API. messages are OpenAI-format; system is first system role content."""
    system_parts: list[str] = []
    anthropic_messages: list[dict[str, Any]] = []
    for m in messages:
        role = (m.get("role") or "").strip().lower()
        content = (m.get("content") or "").strip()
        if role == "system":
            system_parts.append(content)
        elif role in ("user", "assistant"):
            anthropic_messages.append({"role": role, "content": content})
    system = "\n\n".join(system_parts) if system_parts else None
    if not anthropic_messages:
        raise ValueError("No user or assistant messages for Anthropic")
    url = f"{base_url.rstrip('/')}/v1/messages"
    payload: dict[str, Any] = {
        "model": model or "claude-sonnet-4-20250514",
        "max_tokens": 8192,
        "messages": anthropic_messages,
        "temperature": temperature,
    }
    if system:
        payload["system"] = system
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(
            url,
            json=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
    for block in data.get("content") or []:
        if block.get("type") == "text":
            return (block.get("text") or "").strip()
    return ""


def chat_completion(
    messages: list[dict[str, str]],
    temperature: float | None = None,
    model: str | None = None,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    provider: str | None = None,
) -> str:
    """Call OpenAI-compatible or Anthropic chat completion. Profile overrides: base_url, api_key, provider, model, temperature."""
    settings = get_settings()
    use_base = base_url
    use_key = api_key
    use_model = model
    use_temp = temperature
    use_anthropic = False

    if (use_key or use_base or provider) and provider:
        cfg = PROVIDER_CONFIG.get((provider or "").strip().lower())
        if cfg:
            prov_base, use_anthropic = cfg
            if not use_base:
                use_base = prov_base
        if not use_base and not use_key:
            use_base = settings.llm_base_url
            use_key = settings.llm_api_key
    if not use_base:
        use_base = settings.llm_base_url
    if use_key is None or use_key == "":
        use_key = settings.llm_api_key
    if use_model is None or (isinstance(use_model, str) and not use_model.strip()):
        use_model = settings.llm_model
    use_model = (use_model or settings.llm_model).strip() or settings.llm_model
    if use_temp is None:
        use_temp = settings.llm_temperature
    use_temp = float(use_temp)

    if use_anthropic:
        # Anthropic model IDs (e.g. claude-sonnet-4-20250514); profile may store "anthropic/claude-sonnet-4.6" from OpenRouter
        anthropic_model = use_model.replace("anthropic/", "") if use_model.startswith("anthropic/") else use_model
        return _anthropic_messages(use_base, use_key, anthropic_model, messages, use_temp)

    url = f"{use_base.rstrip('/')}/chat/completions"
    payload = {
        "model": use_model,
        "messages": messages,
        "temperature": use_temp,
    }
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {use_key}"},
        )
        resp.raise_for_status()
        data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("No choices in LLM response")
    content = choices[0].get("message", {}).get("content") or ""
    return content.strip()
