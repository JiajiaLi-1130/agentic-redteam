"""Command line entrypoint for the harmless toy agentic framework."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.planner_loop import PlannerLoop


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the toy skill-based safety evaluation framework."
    )
    parser.add_argument("--seed_prompt", required=True, help="Initial prompt to process.")
    parser.add_argument(
        "--workflow",
        default="basic",
        help="Workflow name to use, typically 'basic' or 'escalation'.",
    )
    parser.add_argument(
        "--max_steps",
        type=int,
        default=None,
        help="Optional override for maximum planner steps.",
    )
    parser.add_argument(
        "--planner_backend",
        choices=["rule_based", "openai_compatible"],
        default=None,
        help="Optional planner backend override.",
    )
    parser.add_argument(
        "--planner_base_url",
        default=None,
        help="Optional OpenAI-compatible planner base URL override.",
    )
    parser.add_argument(
        "--planner_model",
        default=None,
        help="Optional OpenAI-compatible planner model name override.",
    )
    parser.add_argument(
        "--planner_api_key",
        default=None,
        help="Optional OpenAI-compatible planner API key override.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the configured workflow and print a compact summary."""
    args = parse_args()
    project_root = Path(__file__).resolve().parent
    planner_overrides: dict[str, object] = {}
    openai_overrides: dict[str, object] = {}
    if args.planner_backend is not None:
        planner_overrides["backend"] = args.planner_backend
    if args.planner_base_url is not None:
        openai_overrides["base_url"] = args.planner_base_url
    if args.planner_model is not None:
        openai_overrides["model"] = args.planner_model
    if args.planner_api_key is not None:
        openai_overrides["api_key"] = args.planner_api_key
    if openai_overrides:
        planner_overrides["openai_compatible"] = openai_overrides

    loop = PlannerLoop(project_root=project_root, planner_overrides=planner_overrides or None)
    summary = loop.run(
        seed_prompt=args.seed_prompt,
        workflow_name=args.workflow,
        max_steps=args.max_steps,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
