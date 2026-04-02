"""Tests for the skill executor."""

from __future__ import annotations

from pathlib import Path

from core.executor import SkillExecutor
from core.registry import SkillRegistry
from core.schemas import SkillContext
from core.skill_loader import SkillLoader


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_executor_runs_toy_skill() -> None:
    """Executor should run one toy skill and parse JSON output."""
    specs = SkillLoader(PROJECT_ROOT).discover()
    registry = SkillRegistry(specs)
    executor = SkillExecutor(PROJECT_ROOT)

    context = SkillContext(
        run_id="test-run",
        step_id=0,
        seed_prompt="Explain the water cycle simply.",
        target_profile={"model_name": "mock-target-model"},
        conversation_history=[],
        memory_summary={},
        constraints={"harmless_only": True},
        prior_candidates=[],
        evaluator_feedback={},
        extra={},
    )

    result = executor.execute(registry.get("toy-persona"), context)

    assert result.skill_name == "toy-persona"
    assert len(result.candidates) == 3
    assert "sanitized_seed" in result.artifacts
