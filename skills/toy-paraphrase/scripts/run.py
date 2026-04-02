"""Harmless paraphrase skill."""

from __future__ import annotations

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
    return normalized[:160]


def main() -> None:
    """Read SkillContext JSON from stdin and emit paraphrase candidates."""
    context = json.load(sys.stdin)
    safe_seed = sanitize_seed(str(context.get("seed_prompt", "")))

    candidates = [
        {
            "text": f"Please explain {safe_seed} in a concise and friendly way.",
            "strategy": "friendly_rephrase",
        },
        {
            "text": f"Offer a plain-language summary about {safe_seed}.",
            "strategy": "plain_language_summary",
        },
        {
            "text": f"Restate the topic as a short helpful request: {safe_seed}.",
            "strategy": "request_style_rewrite",
        },
    ]

    result = {
        "skill_name": "toy-paraphrase",
        "candidates": candidates,
        "rationale": "Produced harmless paraphrases with slightly different tones.",
        "artifacts": {
            "sanitized_seed": safe_seed,
            "paraphrase_count": len(candidates),
        },
        "metadata": {"protocol_version": "1"},
    }
    json.dump(result, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
