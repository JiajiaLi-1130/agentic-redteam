"""Harmless meta-skill that drafts a new toy skill concept from failure patterns."""

from __future__ import annotations

import json
import sys


def main() -> None:
    """Read SkillContext JSON and emit a new toy skill draft."""
    context = json.load(sys.stdin)
    memory_summary = dict(context.get("memory_summary", {}))
    feedback = dict(context.get("evaluator_feedback", {}))

    recent_tags = list(memory_summary.get("recent_failure_tags", []))
    usefulness = float(feedback.get("usefulness_score", 0.0))
    refusal = float(feedback.get("refusal_score", 0.0))

    draft_name = "toy-clarify-and-wrap-draft"
    result = {
        "skill_name": "discover-skill",
        "candidates": [],
        "rationale": "Drafted a new harmless skill concept from repeated toy failure signals.",
        "artifacts": {
            "draft_skill": {
                "name": draft_name,
                "description": (
                    "A toy skill that first clarifies the sanitized topic and then wraps it "
                    "in a short structured request to improve mock usefulness."
                ),
                "triggering_patterns": {
                    "recent_failure_tags": recent_tags,
                    "usefulness_score": usefulness,
                    "refusal_score": refusal,
                },
                "candidate_logic": [
                    "sanitize the seed prompt",
                    "extract a neutral topic phrase",
                    "generate a structured friendly request",
                    "emit harmless variants only",
                ],
            }
        },
        "metadata": {"protocol_version": "1"},
    }
    json.dump(result, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
