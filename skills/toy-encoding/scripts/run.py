"""Harmless encoding transformation skill."""

from __future__ import annotations

import base64
import codecs
import json
import sys


BLOCKED_MARKERS = (
    "bypass",
    "jailbreak",
    "malware",
    "exploit",
    "weapon",
    "phishing",
    "ransomware",
    "steal",
)


def sanitize_seed(text: str) -> str:
    """Replace unsafe-looking input with a harmless placeholder."""
    normalized = " ".join(text.strip().split())
    if not normalized:
        return "a neutral example topic"
    if any(marker in normalized.lower() for marker in BLOCKED_MARKERS):
        return "a harmless educational topic"
    return normalized[:140]


def main() -> None:
    """Read SkillContext and emit SkillExecutionResult."""
    context = json.load(sys.stdin)
    safe_seed = sanitize_seed(str(context.get("seed_prompt", "")))

    rot13_text = codecs.encode(safe_seed, "rot_13")
    b64_text = base64.b64encode(safe_seed.encode("utf-8")).decode("ascii")
    wrapped_json = json.dumps({"request": safe_seed, "mode": "toy-demo"}, ensure_ascii=False)

    candidates = [
        {
            "text": f"ROT13_DEMO::{rot13_text}",
            "strategy": "rot13_demo",
            "decoded_preview": safe_seed,
        },
        {
            "text": f"BASE64_DEMO::{b64_text}",
            "strategy": "base64_demo",
            "decoded_preview": safe_seed,
        },
        {
            "text": f"JSON_WRAP::{wrapped_json}",
            "strategy": "json_wrap",
            "decoded_preview": safe_seed,
        },
    ]

    result = {
        "skill_name": "toy-encoding",
        "candidates": candidates,
        "rationale": "Applied harmless demonstration encodings to the sanitized seed prompt.",
        "artifacts": {
            "sanitized_seed": safe_seed,
            "encoding_count": len(candidates),
        },
        "metadata": {"protocol_version": "1"},
    }
    json.dump(result, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
