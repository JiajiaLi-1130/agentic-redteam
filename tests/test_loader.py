"""Tests for skill discovery and spec loading."""

from __future__ import annotations

from pathlib import Path

from core.registry import SkillRegistry
from core.skill_loader import SkillLoader
from core.utils import read_markdown_frontmatter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REWRITE_SKILLS = {
    "rewrite-char",
    "rewrite-emoji",
    "rewrite-history",
    "rewrite-hypo",
    "rewrite-language",
    "rewrite-literary",
    "rewrite-reverse",
    "rewrite-security",
    "rewrite-space",
    "rewrite-word",
}


def test_loader_discovers_all_skills() -> None:
    """The loader should find all normal and meta skills."""
    loader = SkillLoader(PROJECT_ROOT)
    specs = loader.discover()
    names = {spec.name for spec in specs}

    assert len(specs) == 15
    assert REWRITE_SKILLS.issubset(names)
    assert "refine-skill" in names
    assert "discover-skill" in names
    assert not list(PROJECT_ROOT.glob("skills/*/skill.json"))
    assert not list(PROJECT_ROOT.glob("meta_skills/*/skill.json"))


def test_loader_populates_family_schema_fields() -> None:
    """Loaded specs should expose richer family-schema metadata."""
    loader = SkillLoader(PROJECT_ROOT)
    registry = SkillRegistry(loader.discover())

    rewrite = registry.get("rewrite-emoji")
    language = registry.get("rewrite-language")
    refine = registry.get("refine-skill")

    assert rewrite.family == "rewrite-emoji"
    assert rewrite.status == "active"
    assert "rewrite_request" in rewrite.applicability["prompt_buckets"]
    assert "success" in rewrite.evaluation_focus
    assert rewrite.composition["pipeline_role"] == "seed_transform"
    assert language.parameters_schema["properties"]["language_mix"]["default"] == "medium"
    assert language.inputs == ["SkillContext JSON on stdin"]
    assert language.outputs == ["SkillExecutionResult JSON on stdout"]
    assert refine.composition["pipeline_role"] == "meta_refiner"
    assert set(refine.composition["compatible_families"]) == REWRITE_SKILLS


def test_loader_uses_minimal_frontmatter_plus_directory_conventions() -> None:
    """Executable metadata should come from package conventions, not markdown metadata."""
    skill_doc = PROJECT_ROOT / "skills" / "rewrite-emoji" / "SKILL.md"
    frontmatter = read_markdown_frontmatter(skill_doc)
    skill_text = skill_doc.read_text(encoding="utf-8")

    assert set(frontmatter) == {"name", "description", "metadata"}
    assert frontmatter["metadata"]["version"] == "0.1.0"
    assert "## Runtime Metadata" not in skill_text

    spec = next(spec for spec in SkillLoader(PROJECT_ROOT).discover() if spec.name == "rewrite-emoji")

    assert spec.name == "rewrite-emoji"
    assert spec.entry == "scripts/run.py"
    assert spec.inputs == ["SkillContext JSON on stdin"]
    assert spec.outputs == ["SkillExecutionResult JSON on stdout"]


def test_registry_filters_applicable_skills_by_prompt_bucket() -> None:
    """Registry should use applicability metadata for prompt-bucket filtering."""
    loader = SkillLoader(PROJECT_ROOT)
    registry = SkillRegistry(loader.discover())

    applicable = registry.filter_applicable(
        prompt_bucket="rewrite_request",
        category="attack",
        stage="search",
        names=["rewrite-emoji", "memory-summarize"],
    )

    assert {spec.name for spec in applicable} == {"rewrite-emoji"}


def test_registry_rejects_duplicates_and_builds_planner_cards() -> None:
    """Registry should protect skill identity and expose compact planner cards."""
    specs = SkillLoader(PROJECT_ROOT).discover()
    registry = SkillRegistry(specs)

    try:
        registry.register(registry.get("rewrite-emoji"))
    except ValueError as exc:
        assert "Duplicate skill name" in str(exc)
    else:
        raise AssertionError("duplicate registration should fail")

    cards = registry.planner_cards(names=["rewrite-emoji", "memory-summarize"])

    assert set(cards) == {"rewrite-emoji", "memory-summarize"}
    assert "entry" not in cards["rewrite-emoji"]
    assert cards["rewrite-emoji"]["category"] == "attack"
