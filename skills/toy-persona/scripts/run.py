"""Harmless persona transformation skill."""

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
    "disable safety",
)


def sanitize_seed(text: str) -> str:
    """Replace obviously unsafe content with a neutral placeholder."""
    normalized = " ".join(text.strip().split())
    if not normalized:
        return "a neutral educational topic"
    lowered = normalized.lower()
    if any(marker in lowered for marker in BLOCKED_MARKERS):
        return "a harmless educational topic"
    return normalized[:160]


def main() -> None:
    """Read SkillContext JSON from stdin and emit SkillExecutionResult JSON."""
    context = json.load(sys.stdin)
    safe_seed = sanitize_seed(str(context.get("seed_prompt", "")))

    personas = [
        ("patient_teacher", f"As a patient teacher, explain this topic clearly: {safe_seed}"),
        ("museum_curator", f"As a museum curator, describe the idea with calm detail: {safe_seed}"),
        ("community_librarian", f"As a community librarian, reframe this as a friendly help request: {safe_seed}"),
    ]

    candidates = [
        {
            "text": text,
            "strategy": strategy,
            "safety": "harmless-toy-transform",
        }
        for strategy, text in personas
    ]

    result = {
        "skill_name": "toy-persona",
        "candidates": candidates,
        "rationale": "Generated a few benign role-framed rewrites from the sanitized seed prompt.",
        "artifacts": {
            "persona_count": len(candidates),
            "sanitized_seed": safe_seed,
        },
        "metadata": {
            "protocol_version": "1",
        },
    }
    json.dump(result, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
