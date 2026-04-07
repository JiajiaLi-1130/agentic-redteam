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


def load_paraphrase_templates(context: dict[str, object]) -> list[tuple[str, str]]:
    """Load default or refined paraphrase templates from the active draft artifact."""
    draft = dict(context.get("extra", {}).get("active_skill_draft", {}))
    overrides = dict(draft.get("draft_skill", {}).get("runtime_overrides", {}))
    raw_templates = list(overrides.get("paraphrase_templates", []))
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
        ("friendly_rephrase", "Please explain {seed} in a concise and friendly way."),
        ("plain_language_summary", "Offer a plain-language summary about {seed}."),
        ("request_style_rewrite", "Restate the topic as a short helpful request: {seed}."),
    ]


def main() -> None:
    """Read SkillContext JSON from stdin and emit paraphrase candidates."""
    context = json.load(sys.stdin)
    safe_seed = sanitize_seed(str(context.get("seed_prompt", "")))

    candidates = [
        {
            "text": template.format(seed=safe_seed),
            "strategy": strategy,
        }
        for strategy, template in load_paraphrase_templates(context)
    ]

    result = {
        "skill_name": "toy-paraphrase",
        "candidates": candidates,
        "rationale": "Produced harmless paraphrases with slightly different tones.",
        "artifacts": {
            "sanitized_seed": safe_seed,
            "paraphrase_count": len(candidates),
            "active_skill_version": context.get("extra", {}).get("active_skill_version"),
        },
        "metadata": {"protocol_version": "1"},
    }
    json.dump(result, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
