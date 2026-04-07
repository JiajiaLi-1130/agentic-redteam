"""End-to-end smoke test for the planner loop."""

from __future__ import annotations

import json
from pathlib import Path

from core.planner_loop import PlannerLoop


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_end_to_end_basic_workflow_runs(tmp_path: Path) -> None:
    """Basic workflow should run through multiple steps and write traces."""
    run_root = tmp_path / "runs"
    loop = PlannerLoop(project_root=PROJECT_ROOT, run_root=run_root)

    summary = loop.run(
        seed_prompt="Explain how rainbows form in a friendly tone.",
        workflow_name="basic",
        max_steps=4,
    )

    run_dir = Path(summary["generated_run_dir"])
    final_summary = json.loads((run_dir / "final_summary.json").read_text(encoding="utf-8"))
    state_trace = (run_dir / "state_trace.jsonl").read_text(encoding="utf-8").strip().splitlines()

    assert summary["steps_completed"] >= 3
    assert final_summary["run_id"] == summary["run_id"]
    assert len(state_trace) >= 3
    assert (run_dir / "skill_calls.jsonl").exists()
    assert (run_dir / "selection_calls.jsonl").exists()
    assert (run_dir / "version_events.jsonl").exists()
    assert (run_dir / "evals.jsonl").exists()
    assert "matrix" in summary["memory_summary"]
    assert "path_stats" in summary["memory_summary"]
    assert "family_combination_stats" in summary["memory_summary"]
