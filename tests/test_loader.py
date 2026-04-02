"""Tests for skill discovery and spec loading."""

from __future__ import annotations

from pathlib import Path

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
