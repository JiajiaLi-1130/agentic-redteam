"""Tests for skill discovery and spec loading."""

from __future__ import annotations

from pathlib import Path

from core.registry import SkillRegistry
from core.skill_loader import SkillLoader


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_loader_discovers_all_skills() -> None:
    """The loader should find all normal and meta skills."""
    loader = SkillLoader(PROJECT_ROOT)
    specs = loader.discover()
    names = {spec.name for spec in specs}

    assert len(specs) == 9
    assert "toy-persona" in names
    assert "evaluation-mock" in names
    assert "refine-skill" in names
    assert "discover-skill" in names


def test_loader_populates_family_schema_fields() -> None:
    """Loaded specs should expose richer family-schema metadata."""
    loader = SkillLoader(PROJECT_ROOT)
    registry = SkillRegistry(loader.discover())

    encoding = registry.get("toy-encoding")
    refine = registry.get("refine-skill")

    assert encoding.family == "toy-encoding"
    assert encoding.status == "active"
    assert "structured_request" in encoding.applicability["prompt_buckets"]
    assert "diversity_score" in encoding.evaluation_focus
    assert "toy-paraphrase" in encoding.composition["compatible_families"]
    assert refine.composition["pipeline_role"] == "meta_refiner"


def test_registry_filters_applicable_skills_by_prompt_bucket() -> None:
    """Registry should use applicability metadata for prompt-bucket filtering."""
    loader = SkillLoader(PROJECT_ROOT)
    registry = SkillRegistry(loader.discover())

    applicable = registry.filter_applicable(
        prompt_bucket="structured_request",
        category="attack",
        stage="search",
        names=["toy-persona", "toy-encoding"],
    )

    assert {spec.name for spec in applicable} == {"toy-encoding", "toy-persona"}
