"""Supplementary harmless evaluation skill."""

from __future__ import annotations

import json
import sys


def _rank_bundles(score_bundles: list[dict[str, object]]) -> list[dict[str, object]]:
    """Sort score bundles by safety outcome."""
    return sorted(
        score_bundles,
        key=lambda bundle: (
            bool(bundle.get("candidate_success", False)),
            -float(bundle.get("response_risk_score", 0.0)),
            -float(bundle.get("refusal_score", 0.0)),
        ),
        reverse=True,
    )


def main() -> None:
    """Read SkillContext JSON and emit toy evaluation notes."""
    context = json.load(sys.stdin)
    candidates = list(context.get("prior_candidates", []))
    responses = list(context.get("extra", {}).get("last_responses", []))
    precomputed = dict(context.get("extra", {}).get("precomputed_eval", {}))
    metadata = dict(precomputed.get("metadata", {}))
    score_bundles = list(metadata.get("score_bundles", []))

    strategy_names = [candidate.get("strategy", "unknown") for candidate in candidates]
    response_styles = [response.get("style", "unknown") for response in responses]
    best_index = metadata.get("best_candidate_index")
    guard_backend = metadata.get("guard_backend", "disabled")
    ranked_bundles = _rank_bundles(score_bundles)

    notes = [
        f"Observed strategies: {', '.join(strategy_names) if strategy_names else 'none'}.",
        f"Observed response styles: {', '.join(response_styles) if response_styles else 'none'}.",
        f"Guard backend status: {guard_backend}.",
    ]
    if isinstance(best_index, int) and 0 <= best_index < len(candidates):
        notes.append(f"Best candidate index in toy evaluation: {best_index}.")
    else:
        notes.append("No clear best candidate index was available.")

    if ranked_bundles:
        top_bundle = ranked_bundles[0]
        notes.append(
            "Top bundle summary: "
            f"success={bool(top_bundle.get('candidate_success', False))}, "
            f"request_risk={float(top_bundle.get('request_risk_score', 0.0)):.2f}, "
            f"response_risk={float(top_bundle.get('response_risk_score', 0.0)):.2f}, "
            f"refusal={float(top_bundle.get('refusal_score', 0.0)):.2f}."
        )

    result = {
        "skill_name": "evaluation-mock",
        "candidates": [],
        "rationale": "Added bundle-aware human-readable notes to the kernel evaluator output.",
        "artifacts": {
            "notes": notes,
            "strategy_names": strategy_names,
            "response_styles": response_styles,
            "guard_backend": guard_backend,
            "ranked_candidates": [
                {
                    "candidate_index": int(bundle.get("candidate_index", -1)),
                    "strategy": bundle.get("strategy", "unknown"),
                    "candidate_success": bool(bundle.get("candidate_success", False)),
                    "request_safety_label": bundle.get("request_safety_label", "not_scored"),
                    "response_safety_label": bundle.get("response_safety_label", "not_scored"),
                    "refusal_label": bundle.get("refusal_label"),
                }
                for bundle in ranked_bundles
            ],
        },
        "metadata": {"protocol_version": "1"},
    }
    json.dump(result, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
