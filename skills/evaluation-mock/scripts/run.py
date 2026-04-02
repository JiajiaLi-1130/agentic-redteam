"""Supplementary harmless evaluation skill."""

from __future__ import annotations

import json
import sys


def main() -> None:
    """Read SkillContext JSON and emit toy evaluation notes."""
    context = json.load(sys.stdin)
    candidates = list(context.get("prior_candidates", []))
    responses = list(context.get("extra", {}).get("last_responses", []))
    precomputed = dict(context.get("extra", {}).get("precomputed_eval", {}))

    strategy_names = [candidate.get("strategy", "unknown") for candidate in candidates]
    response_styles = [response.get("style", "unknown") for response in responses]
    best_index = precomputed.get("metadata", {}).get("best_candidate_index")

    notes = [
        f"Observed strategies: {', '.join(strategy_names) if strategy_names else 'none'}.",
        f"Observed response styles: {', '.join(response_styles) if response_styles else 'none'}.",
    ]
    if isinstance(best_index, int) and 0 <= best_index < len(candidates):
        notes.append(f"Best candidate index in toy evaluation: {best_index}.")
    else:
        notes.append("No clear best candidate index was available.")

    result = {
        "skill_name": "evaluation-mock",
        "candidates": [],
        "rationale": "Added supplementary human-readable notes to the kernel evaluator output.",
        "artifacts": {
            "notes": notes,
            "strategy_names": strategy_names,
            "response_styles": response_styles,
        },
        "metadata": {"protocol_version": "1"},
    }
    json.dump(result, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
