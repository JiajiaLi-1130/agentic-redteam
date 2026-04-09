"""Shared OpenAI-compatible helper for model-backed meta-skills."""

from __future__ import annotations

import json
from typing import Any
from urllib import error, request


def generate_meta_artifact(
    *,
    backend_config: dict[str, Any],
    system_prompt: str,
    user_payload: dict[str, Any],
    fallback_payload: dict[str, Any],
    fallback_rationale: str,
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """Generate one structured meta-skill artifact from a remote model or fallback."""
    enabled = bool(backend_config.get("enabled", False))
    base_url = str(backend_config.get("base_url", "")).rstrip("/")
    model = str(backend_config.get("model", ""))
    api_key = str(backend_config.get("api_key", ""))
    timeout_seconds = int(backend_config.get("timeout_seconds", 8))
    temperature = float(backend_config.get("temperature", 0.2))
    max_tokens = int(backend_config.get("max_tokens", 1200))
    fallback_to_template = bool(backend_config.get("fallback_to_template", True))

    if not enabled:
        return (
            fallback_payload,
            fallback_rationale,
            {
                "backend": "template_fallback",
                "fallback_reason": "meta_skill_backend_disabled",
            },
        )

    if not base_url or not model:
        return (
            fallback_payload,
            fallback_rationale,
            {
                "backend": "template_fallback",
                "fallback_reason": "meta_skill_backend_missing_base_url_or_model",
            },
        )

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        content = _extract_content(payload)
        parsed = json.loads(_extract_json_object(content))
        artifacts = dict(parsed.get("artifacts", {}))
        rationale = str(parsed.get("rationale", "")).strip() or fallback_rationale
        return (
            artifacts or fallback_payload,
            rationale,
            {
                "backend": "openai_compatible",
                "model": model,
                "fallback_reason": None,
            },
        )
    except Exception as exc:
        if not fallback_to_template:
            raise
        return (
            fallback_payload,
            fallback_rationale,
            {
                "backend": "template_fallback",
                "fallback_reason": str(exc),
            },
        )


def _extract_content(payload: dict[str, Any]) -> str:
    """Extract chat content from an OpenAI-compatible payload."""
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected meta-skill response payload: {payload}") from exc

    if isinstance(content, list):
        text_parts = [str(item.get("text", "")) for item in content if isinstance(item, dict)]
        return "\n".join(part for part in text_parts if part).strip()
    return str(content).strip()


def _extract_json_object(text: str) -> str:
    """Extract one JSON object from plain text or fenced output."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            stripped = "\n".join(lines[1:-1]).strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError(f"Meta-skill model did not return a JSON object: {text}")
    return stripped[start : end + 1]
