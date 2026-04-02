"""Harmless meta-skill that drafts a composite toy skill."""

from __future__ import annotations

import json
import sys


def main() -> None:
    """Read SkillContext JSON and emit a combined toy skill draft."""
    context = json.load(sys.stdin)
    target_specs = list(context.get("extra", {}).get("target_skill_specs", []))
    names = [spec.get("name", "unknown") for spec in target_specs[:2]]
    if len(names) < 2:
        names = names + ["toy-paraphrase"] * (2 - len(names))

    combined_name = f"{names[0]}-{names[1]}-combo-draft"
    result = {
        "skill_name": "combine-skills",
        "candidates": [],
        "rationale": "Drafted a harmless composite skill concept from two existing toy skills.",
        "artifacts": {
            "draft_skill": {
                "name": combined_name,
                "base_skills": names[:2],
                "description": (
                    "A toy draft that first applies the first skill's framing and then "
                    "uses the second skill's wording style."
                ),
                "candidate_logic": [
                    "sanitize the seed prompt",
                    "apply the first toy transform",
                    "apply the second toy transform",
                    "emit 2-3 harmless variants",
                ],
            }
        },
        "metadata": {"protocol_version": "1"},
    }
    json.dump(result, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
