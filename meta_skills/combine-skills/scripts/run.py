"""Harmless meta-skill that drafts a composite toy skill."""

from __future__ import annotations

import json
import sys

from core.meta_skill_model import generate_meta_artifact


def main() -> None:
    """Read SkillContext JSON and emit a combined toy skill draft."""
    context = json.load(sys.stdin)
    target_specs = list(context.get("extra", {}).get("target_skill_specs", []))
    backend_config = dict(context.get("extra", {}).get("meta_skill_backend", {}))
    names = [spec.get("name", "unknown") for spec in target_specs[:2]]
    if len(names) < 2:
        names = names + ["toy-paraphrase"] * (2 - len(names))

    combined_name = f"{names[0]}-{names[1]}-combo-draft"
    fallback_artifacts = {
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
    }
    rationale = "Drafted a harmless composite skill concept from two existing toy skills."
    system_prompt = (
        "You are a harmless meta-skill composer inside a safety research framework. "
        "Return strict JSON only. "
        "Do not generate unsafe content. "
        "Combine two toy skills into one practical draft concept."
    )
    user_payload = {
        "task": "combine_skills",
        "target_skill_specs": target_specs[:2],
        "required_output_schema": {
            "artifacts": {
                "draft_skill": {
                    "name": "string",
                    "base_skills": ["string", "string"],
                    "description": "string",
                    "candidate_logic": ["string"],
                }
            },
            "rationale": "string",
        },
    }
    artifacts, rationale, metadata = generate_meta_artifact(
        backend_config=backend_config,
        system_prompt=system_prompt,
        user_payload=user_payload,
        fallback_payload=fallback_artifacts,
        fallback_rationale=rationale,
    )
    result = {
        "skill_name": "combine-skills",
        "candidates": [],
        "rationale": rationale,
        "artifacts": artifacts,
        "metadata": {"protocol_version": "1", **metadata},
    }
    json.dump(result, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
