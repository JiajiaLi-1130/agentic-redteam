"""Shared runtime helpers for model-backed skill scripts."""

from __future__ import annotations

import json
from typing import Any

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional runtime dependency
    OpenAI = None


def extract_content(payload: dict[str, Any]) -> str:
    """Extract assistant content from an OpenAI-compatible payload."""
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected model response payload: {payload}") from exc
    if isinstance(content, list):
        text_parts = [str(item.get("text", "")) for item in content if isinstance(item, dict)]
        return "\n".join(part for part in text_parts if part).strip()
    return str(content).strip()


def extract_json_object(text: str) -> str:
    """Extract one JSON object from plain text or fenced output."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            stripped = "\n".join(lines[1:-1]).strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError(f"Model response did not contain a JSON object: {text}")
    return stripped[start : end + 1]


def parse_candidate_count(
    action_args: dict[str, Any],
    *,
    default: int = 1,
    minimum: int = 1,
    maximum: int = 5,
) -> int:
    """Parse and clamp candidate_count from runtime action args."""
    raw_value = action_args.get("candidate_count", default)
    try:
        requested_count = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid candidate_count: {raw_value}") from exc
    return min(max(requested_count, minimum), maximum)


def parse_enum_arg(
    action_args: dict[str, Any],
    *,
    key: str,
    allowed: set[str],
    default: str,
) -> str:
    """Parse a string enum argument and fall back to the configured default."""
    value = str(action_args.get(key, default)).strip().lower()
    if value not in allowed:
        return default
    return value


def request_model_json_candidates(
    *,
    backend_config: dict[str, Any],
    user_prompt: str,
    candidate_count: int,
    default_strategy_prefix: str,
    style: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Request candidates from an OpenAI-compatible backend and normalize them."""
    enabled = bool(backend_config.get("enabled", False))
    base_url = str(backend_config.get("base_url", "")).rstrip("/")
    model = str(backend_config.get("model", ""))
    api_key = str(backend_config.get("api_key", ""))
    timeout_seconds = int(backend_config.get("timeout_seconds", 12))
    temperature = float(backend_config.get("temperature", 0.9))
    max_tokens = int(backend_config.get("max_tokens", 1000))

    if not enabled:
        raise RuntimeError("skill_model_backend_disabled")
    if not base_url or not model:
        raise RuntimeError("skill_model_backend_missing_base_url_or_model")
    if OpenAI is None:
        raise RuntimeError("openai_package_not_installed")

    client = OpenAI(base_url=base_url, api_key=api_key)

    def _request_completion(*, force_json: bool) -> dict[str, Any]:
        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that strictly follows instructions. "
                        "You output only valid JSON and nothing else."
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout_seconds,
        }
        if force_json:
            request_kwargs["response_format"] = {"type": "json_object"}

        completion = client.chat.completions.create(**request_kwargs)
        return completion.model_dump()

    try:
        payload = _request_completion(force_json=True)
    except Exception:
        try:
            payload = _request_completion(force_json=False)
        except Exception as retry_exc:
            raise RuntimeError(f"Model backend request failed: {retry_exc}") from retry_exc

    try:
        parsed = json.loads(extract_json_object(extract_content(payload)))
    except Exception as exc:
        raise RuntimeError(
            "Model response was not valid JSON. Ensure the backend supports JSON mode or "
            "returns raw JSON without extra text."
        ) from exc

    raw_candidates = list(parsed.get("candidates", []))
    if not raw_candidates:
        raise RuntimeError("model_returned_no_candidates")

    candidates: list[dict[str, str]] = []
    for index, item in enumerate(raw_candidates[:candidate_count], start=1):
        if not isinstance(item, dict):
            continue
        text = " ".join(str(item.get("text", "")).split()).strip()
        strategy = " ".join(
            str(item.get("strategy", f"{default_strategy_prefix}_{index}")).split()
        ).strip()
        if text:
            candidates.append(
                {
                    "text": text,
                    "strategy": strategy or f"{default_strategy_prefix}_{index}",
                    "style": style,
                }
            )

    if not candidates:
        raise RuntimeError("model_candidates_were_empty")
    if len(candidates) != candidate_count:
        raise RuntimeError(
            f"model_returned_wrong_candidate_count: expected {candidate_count}, got {len(candidates)}"
        )

    return candidates, {
        "backend": "openai_compatible",
        "model": model,
    }
