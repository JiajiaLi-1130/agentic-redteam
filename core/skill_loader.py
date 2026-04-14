"""Load skill specifications from SKILL.md package metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from core.schemas import SkillSpec
from core.utils import read_markdown_frontmatter


class SkillLoader:
    """Discover and validate skills under configured roots."""

    REQUIRED_FIELDS = {
        "name",
        "version",
        "description",
        "category",
        "stage",
        "entry",
    }
    OPTIONAL_LIST_FIELDS = {
        "tags",
        "inputs",
        "outputs",
        "references",
        "failure_modes",
    }
    FRONTMATTER_REQUIRED_FIELDS = {"name", "description"}

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
            for skill_doc in sorted(root.glob("*/SKILL.md")):
                spec = self._load_one(skill_doc)
                if spec is not None:
                    specs.append(spec)
        return specs

    def _load_one(self, skill_doc: Path) -> SkillSpec | None:
        """Load and validate one indexed skill spec from SKILL.md metadata."""
        frontmatter = read_markdown_frontmatter(skill_doc)
        if not frontmatter:
            return None

        body_metadata = self._read_runtime_metadata(skill_doc)
        if not body_metadata:
            return None

        raw = {
            **body_metadata,
            "name": frontmatter.get("name", body_metadata.get("name", "")),
            "description": frontmatter.get("description", body_metadata.get("description", "")),
            "version": self._frontmatter_version(frontmatter, body_metadata),
        }
        missing = self.REQUIRED_FIELDS - set(raw)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"Missing runtime metadata fields in {skill_doc}: {missing_text}")
        for field_name in self.OPTIONAL_LIST_FIELDS:
            raw.setdefault(field_name, [])

        self._validate_frontmatter(skill_doc, raw)

        spec = SkillSpec.from_dict(raw)
        spec.root_dir = str(skill_doc.parent.resolve())
        entry_path = skill_doc.parent / spec.entry
        if not entry_path.exists():
            raise ValueError(f"Missing entry script for {spec.name}: {entry_path}")

        for reference in spec.references:
            ref_path = skill_doc.parent / reference
            if not ref_path.exists():
                raise ValueError(f"Missing reference for {spec.name}: {ref_path}")

        return spec

    def _read_runtime_metadata(self, skill_doc: Path) -> dict[str, Any]:
        """Read the Runtime Metadata YAML block from the markdown body."""
        text = skill_doc.read_text(encoding="utf-8")
        marker = "## Runtime Metadata"
        marker_index = text.find(marker)
        if marker_index == -1:
            return {}

        fenced_start = text.find("```yaml", marker_index)
        if fenced_start == -1:
            return {}
        payload_start = text.find("\n", fenced_start)
        if payload_start == -1:
            return {}
        payload_end = text.find("```", payload_start + 1)
        if payload_end == -1:
            return {}

        return yaml.safe_load(text[payload_start + 1:payload_end]) or {}

    def _frontmatter_version(
        self,
        frontmatter: dict[str, Any],
        body_metadata: dict[str, Any],
    ) -> str:
        """Resolve version from minimal frontmatter before falling back to body metadata."""
        metadata = frontmatter.get("metadata", {})
        if isinstance(metadata, dict) and metadata.get("version") is not None:
            return str(metadata["version"])
        if frontmatter.get("version") is not None:
            return str(frontmatter["version"])
        return str(body_metadata.get("version", ""))

    def _validate_frontmatter(self, skill_doc: Path, raw_spec: dict[str, object]) -> None:
        """Validate that SKILL.md frontmatter matches the declarative spec."""
        frontmatter = read_markdown_frontmatter(skill_doc)
        if not frontmatter:
            raise ValueError(f"Missing YAML frontmatter in {skill_doc}")

        missing = self.FRONTMATTER_REQUIRED_FIELDS - set(frontmatter)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"Missing frontmatter fields in {skill_doc}: {missing_text}")

        if str(frontmatter.get("name")) != str(raw_spec["name"]):
            raise ValueError(f"Frontmatter name mismatch in {skill_doc}")
        if str(frontmatter.get("description")) != str(raw_spec["description"]):
            raise ValueError(f"Frontmatter description mismatch in {skill_doc}")

        metadata = frontmatter.get("metadata", {})
        frontmatter_version = metadata.get("version") if isinstance(metadata, dict) else None
        if frontmatter_version is None:
            frontmatter_version = frontmatter.get("version")
        if frontmatter_version is not None and str(frontmatter_version) != str(raw_spec["version"]):
            raise ValueError(f"Frontmatter version mismatch in {skill_doc}")
