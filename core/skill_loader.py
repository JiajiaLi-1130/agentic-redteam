"""Load skill specifications from skill package directories."""

from __future__ import annotations

from pathlib import Path

from core.schemas import SkillSpec
from core.utils import read_json


class SkillLoader:
    """Discover and validate skills under configured roots."""

    REQUIRED_FIELDS = {
        "name",
        "version",
        "description",
        "category",
        "stage",
        "tags",
        "inputs",
        "outputs",
        "entry",
        "references",
        "failure_modes",
    }

    def __init__(self, project_root: Path, skill_roots: list[Path] | None = None) -> None:
        self.project_root = project_root
        self.skill_roots = skill_roots or [
            project_root / "skills",
            project_root / "meta_skills",
        ]

    def discover(self) -> list[SkillSpec]:
        """Scan all roots and return validated specs."""
        specs: list[SkillSpec] = []
        for root in self.skill_roots:
            if not root.exists():
                continue
            for spec_path in sorted(root.glob("*/skill.json")):
                specs.append(self._load_one(spec_path))
        return specs

    def _load_one(self, spec_path: Path) -> SkillSpec:
        """Load and validate one skill spec."""
        raw = read_json(spec_path)
        missing = self.REQUIRED_FIELDS - set(raw)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"Missing fields in {spec_path}: {missing_text}")

        spec = SkillSpec.from_dict(raw)
        spec.root_dir = str(spec_path.parent.resolve())

        entry_path = spec_path.parent / spec.entry
        if not entry_path.exists():
            raise ValueError(f"Missing entry script for {spec.name}: {entry_path}")

        skill_doc = spec_path.parent / "SKILL.md"
        if not skill_doc.exists():
            raise ValueError(f"Missing SKILL.md for {spec.name}")

        for reference in spec.references:
            ref_path = spec_path.parent / reference
            if not ref_path.exists():
                raise ValueError(f"Missing reference for {spec.name}: {ref_path}")

        return spec
