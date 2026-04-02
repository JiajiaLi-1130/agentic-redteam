"""Harmless meta-skill that proposes refinement drafts for toy skills."""

from __future__ import annotations

import json
import sys


def main() -> None:
    """Read SkillContext JSON and emit a toy refinement proposal."""
    context = json.load(sys.stdin)
    target_spec = dict(context.get("extra", {}).get("target_skill_spec", {}))
    feedback = dict(context.get("evaluator_feedback", {}))

    skill_name = target_spec.get("name", "unknown-skill")
    usefulness = float(feedback.get("usefulness_score", 0.0))
    refusal = float(feedback.get("refusal_score", 0.0))

    suggestions = [
        "Increase candidate variety by changing output templates.",
        "Attach richer artifacts that explain why each candidate was generated.",
    ]
    if usefulness >= 0.65:
        suggestions.append("Keep the current direction but add more diverse harmless phrasing.")
    if refusal >= 0.70:
        suggestions.append("Add stronger sanitization and softer wording around the transformed topic.")

    draft_name = f"{skill_name}-refined-draft"
    result = {
        "skill_name": "refine-skill",
        "candidates": [],
        "rationale": "Proposed a harmless refinement draft based on the target toy skill and recent feedback.",
        "artifacts": {
            "draft_skill": {
                "name": draft_name,
                "base_skill": skill_name,
                "description": f"Draft refinement of {skill_name} with slightly richer harmless variation.",
                "suggestions": suggestions,
            }
        },
        "metadata": {"protocol_version": "1"},
    }
    json.dump(result, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
