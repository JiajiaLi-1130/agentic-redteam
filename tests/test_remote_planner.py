"""Tests for the optional OpenAI-compatible remote planner backend."""

from __future__ import annotations

from pathlib import Path

from core.planner import OpenAICompatiblePlanner
from core.registry import SkillRegistry
from core.schemas import AgentState
from core.skill_loader import SkillLoader
from core.workflow import Workflow


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_workflows() -> dict[str, Workflow]:
    """Load workflow fixtures from the project."""
    basic = Workflow.from_file(PROJECT_ROOT / "configs" / "workflows" / "basic.yaml")
    escalation = Workflow.from_file(PROJECT_ROOT / "configs" / "workflows" / "escalation.yaml")
    return {"basic": basic, "escalation": escalation}


def make_state() -> AgentState:
    """Create a default planner state."""
    return AgentState(
        run_id="test-run",
        current_step=0,
        seed_prompt="Explain clouds.",
        memory_summary={
            "total_entries": 0,
            "skill_counts": {},
            "recent_skill_names": [],
            "recent_failure_tags": [],
        },
        last_eval={},
        active_workflow_stage="search",
        available_skills=[],
        budget_remaining={"steps": 5, "skill_calls": 10, "environment_calls": 10},
    )


def test_remote_planner_accepts_valid_json(monkeypatch) -> None:
    """Remote planner should accept a valid structured response."""
    specs = SkillLoader(PROJECT_ROOT).discover()
    registry = SkillRegistry(specs)
    planner = OpenAICompatiblePlanner(
        {
            "base_url": "http://example.invalid/v1",
            "model": "orm",
            "api_key": "FAKE_API_KEY",
        }
    )
    state = make_state()

    monkeypatch.setattr(
        planner,
        "_call_remote_planner",
        lambda **_kwargs: (
            '{"plan_steps": ['
            '{"action_type": "invoke_skill", "target": "toy-encoding", "args": {"mode": "search"}, "reason": "Try structured transforms."},'
            '{"action_type": "invoke_skill", "target": "toy-persona", "args": {"mode": "search"}, "reason": "Try role framing."}'
            "]}"),
    )

    plan = planner.plan(state, load_workflows(), registry)

    assert [step.target for step in plan] == ["toy-encoding", "toy-persona"]
    assert state.planner_flags["planner_backend"] == "openai_compatible"


def test_remote_planner_falls_back_on_invalid_json(monkeypatch) -> None:
    """Remote planner should fallback to rule-based planning on invalid output."""
    specs = SkillLoader(PROJECT_ROOT).discover()
    registry = SkillRegistry(specs)
    planner = OpenAICompatiblePlanner(
        {
            "base_url": "http://example.invalid/v1",
            "model": "orm",
            "api_key": "FAKE_API_KEY",
        }
    )
    state = make_state()

    monkeypatch.setattr(planner, "_call_remote_planner", lambda **_kwargs: "not json at all")

    plan = planner.plan(state, load_workflows(), registry)

    assert len(plan) == 2
    assert all(step.action_type == "invoke_skill" for step in plan)
    assert state.planner_flags["planner_mode"] == "remote_fallback"
