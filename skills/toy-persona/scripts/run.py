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


def load_persona_templates(context: dict[str, object]) -> list[tuple[str, str]]:
    """Load default or refined persona templates from the active draft artifact."""
    draft = dict(context.get("extra", {}).get("active_skill_draft", {}))
    overrides = dict(draft.get("draft_skill", {}).get("runtime_overrides", {}))
    raw_templates = list(overrides.get("persona_templates", []))
    templates: list[tuple[str, str]] = []
    for item in raw_templates:
        if not isinstance(item, dict):
            continue
        strategy = str(item.get("strategy", "")).strip()
        template = str(item.get("template", "")).strip()
        if strategy and template:
            templates.append((strategy, template))

    if templates:
        limit = int(overrides.get("max_candidates", len(templates)))
        return templates[: max(limit, 1)]

    return [
        ("patient_teacher", "As a patient teacher, explain this topic clearly: {seed}"),
        ("museum_curator", "As a museum curator, describe the idea with calm detail: {seed}"),
        ("community_librarian", "As a community librarian, reframe this as a friendly help request: {seed}"),
    ]


def main() -> None:
    """Read SkillContext JSON from stdin and emit SkillExecutionResult JSON."""
    context = json.load(sys.stdin)
    safe_seed = sanitize_seed(str(context.get("seed_prompt", "")))

    personas = [
        (strategy, template.format(seed=safe_seed))
        for strategy, template in load_persona_templates(context)
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
            "active_skill_version": context.get("extra", {}).get("active_skill_version"),
        },
        "metadata": {
            "protocol_version": "1",
        },
    }
    json.dump(result, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
