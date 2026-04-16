"""Load skill specifications from SKILL.md frontmatter and directory conventions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.schemas import SkillSpec
from core.utils import read_markdown_frontmatter


class SkillLoader:
    """Discover and validate skills under configured roots."""

    FRONTMATTER_REQUIRED_FIELDS = {"name", "description"}
    DEFAULT_ENTRY = "scripts/run.py"
    PROTOCOL_INPUTS = ["SkillContext JSON on stdin"]
    PROTOCOL_OUTPUTS = ["SkillExecutionResult JSON on stdout"]
    REWRITE_SKILL_NAMES = [
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
    ]

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
        """Load and validate one indexed skill spec from package conventions."""
        frontmatter = read_markdown_frontmatter(skill_doc)
        if not frontmatter:
            return None

        raw = self._spec_from_conventions(skill_doc, frontmatter)
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

    def _spec_from_conventions(self, skill_doc: Path, frontmatter: dict[str, Any]) -> dict[str, Any]:
        """Build a machine spec from package location and minimal frontmatter."""
        name = str(frontmatter.get("name", skill_doc.parent.name))
        raw = {
            "name": name,
            "version": self._frontmatter_version(frontmatter),
            "description": str(frontmatter.get("description", "")),
            "category": self._category_for(skill_doc, name),
            "stage": self._stages_for(skill_doc, name),
            "tags": self._tags_for(skill_doc, name),
            "inputs": list(self.PROTOCOL_INPUTS),
            "outputs": list(self.PROTOCOL_OUTPUTS),
            "entry": self.DEFAULT_ENTRY,
            "references": self._references_for(skill_doc),
            "failure_modes": [],
            "family": name,
            "variant": f"{name}-core",
            "status": "active",
            "applicability": self._applicability_for(skill_doc, name),
            "parameters_schema": self._parameters_schema_for(name),
            "retrieval_hints": self._retrieval_hints_for(skill_doc, name),
            "composition": self._composition_for(skill_doc, name),
            "refinement": self._refinement_for(skill_doc, name),
            "evaluation_focus": self._evaluation_focus_for(skill_doc, name),
            "safety_scope": self._safety_scope_for(skill_doc, name),
        }
        return raw

    def _frontmatter_version(self, frontmatter: dict[str, Any]) -> str:
        """Resolve version from minimal frontmatter."""
        metadata = frontmatter.get("metadata", {})
        if isinstance(metadata, dict) and metadata.get("version") is not None:
            return str(metadata["version"])
        if frontmatter.get("version") is not None:
            return str(frontmatter["version"])
        return "1.0"

    def _category_for(self, skill_doc: Path, name: str) -> str:
        """Infer category from the package root and directory name."""
        if self._is_meta_skill(skill_doc):
            return "meta"
        if name in {"memory-summarize", "retrieval-analysis"}:
            return "analysis"
        return "attack"

    def _stages_for(self, skill_doc: Path, name: str) -> list[str]:
        """Infer valid workflow stages from directory conventions."""
        if self._is_meta_skill(skill_doc):
            if name == "discover-skill":
                return ["escalation"]
            return ["refine", "escalation"]
        if name in {"memory-summarize", "retrieval-analysis"}:
            return ["analysis", "escalation"]
        return ["search"]

    def _tags_for(self, skill_doc: Path, name: str) -> list[str]:
        """Infer simple tags from package kind and name tokens."""
        tags = [token for token in name.split("-") if token]
        category = self._category_for(skill_doc, name)
        if category not in tags:
            tags.append(category)
        return tags

    def _references_for(self, skill_doc: Path) -> list[str]:
        """Discover reference files by convention."""
        references_dir = skill_doc.parent / "references"
        if not references_dir.exists():
            return []
        return [
            str(path.relative_to(skill_doc.parent))
            for path in sorted(references_dir.glob("*"))
            if path.is_file()
        ]

    def _applicability_for(self, skill_doc: Path, name: str) -> dict[str, Any]:
        """Infer broad applicability hints for planner cards."""
        category = self._category_for(skill_doc, name)
        if name.startswith("rewrite-"):
            memory_tags = [token for token in name.split("-") if token]
            return {
                "prompt_buckets": ["rewrite_request", "style_transfer", "safety_sensitive", "general"],
                "target_traits": ["chat", "instruction_following"],
                "memory_tags": memory_tags,
                "preferred_stages": ["search"],
            }
        if category == "analysis":
            return {
                "prompt_buckets": ["general"],
                "target_traits": [],
                "memory_tags": ["high_refusal", "failure_pattern", "analysis_needed"],
                "preferred_stages": ["analysis", "escalation"],
            }
        return {
            "prompt_buckets": ["general"],
            "target_traits": [],
            "memory_tags": ["high_refusal", "useful", "needs_refinement"],
            "preferred_stages": self._stages_for(skill_doc, name),
        }

    def _parameters_schema_for(self, name: str) -> dict[str, Any]:
        """Infer optional action args for known package conventions."""
        rewrite_style_fields = {
            "rewrite-char": ("char_intensity", ["light", "medium", "high"], "medium"),
            "rewrite-emoji": ("emoji_density", ["light", "medium", "high"], "medium"),
            "rewrite-history": ("history_tense", ["past_simple", "past_perfect", "mixed_past"], "past_simple"),
            "rewrite-hypo": ("hypo_frame", ["imagine_if", "suppose_that", "what_if"], "imagine_if"),
            "rewrite-language": ("language_mix", ["light", "medium", "high"], "medium"),
            "rewrite-literary": (
                "literary_style",
                ["poetic", "narrative", "philosophical", "dramatic"],
                "poetic",
            ),
            "rewrite-reverse": ("reverse_mode", ["protective", "preventive", "contrastive"], "protective"),
            "rewrite-security": ("security_frame", ["audit", "compliance", "defense_review"], "audit"),
            "rewrite-space": ("space_frame", ["virtual_world", "futuristic", "mythic_realm"], "virtual_world"),
            "rewrite-word": ("word_style", ["euphemistic", "indirect", "ambiguous"], "euphemistic"),
        }
        if name in rewrite_style_fields:
            field_name, enum_values, default_value = rewrite_style_fields[name]
            return {
                "type": "object",
                "properties": {
                    "candidate_count": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "default": 1,
                    },
                    field_name: {
                        "type": "string",
                        "enum": enum_values,
                        "default": default_value,
                    },
                },
                "required": [],
            }
        return {"type": "object", "properties": {}, "required": []}

    def _retrieval_hints_for(self, skill_doc: Path, name: str) -> dict[str, Any]:
        """Infer lightweight retrieval hints."""
        if name.startswith("rewrite-"):
            return {
                "lexical_triggers": [token for token in name.split("-") if token] + ["rewrite", "rephrase"],
                "memory_keys": ["risk_matrix", "recent_skill_names", name],
                "prompt_buckets": ["rewrite_request", "style_transfer", "general"],
            }
        category = self._category_for(skill_doc, name)
        return {
            "lexical_triggers": [token for token in name.split("-") if token],
            "memory_keys": ["recent_memory", "risk_matrix", name],
            "prompt_buckets": ["general"],
        }

    def _composition_for(self, skill_doc: Path, name: str) -> dict[str, Any]:
        """Infer composition hints used by planner cards."""
        if self._is_meta_skill(skill_doc):
            role = {
                "combine-skills": "meta_composer",
                "discover-skill": "meta_discovery",
                "refine-skill": "meta_refiner",
            }.get(name, "meta")
            return {
                "compatible_families": list(self.REWRITE_SKILL_NAMES),
                "conflicts_with": [],
                "pipeline_role": role,
            }
        if name == "memory-summarize":
            return {
                "compatible_families": ["retrieval-analysis"],
                "conflicts_with": [],
                "pipeline_role": "memory_summary",
            }
        if name == "retrieval-analysis":
            return {
                "compatible_families": ["memory-summarize", "refine-skill", "discover-skill"],
                "conflicts_with": [],
                "pipeline_role": "memory_analysis",
            }
        return {
            "compatible_families": [],
            "conflicts_with": [],
            "pipeline_role": "seed_transform",
        }

    def _refinement_for(self, skill_doc: Path, name: str) -> dict[str, Any]:
        """Infer refinement hints."""
        if name.startswith("rewrite-"):
            return {
                "allowed_operations": ["patch_suggestions", "draft_variant"],
                "mutable_fields": ["prompt_instructions", "candidate_count", "style_parameters", "sampling_params"],
                "promotion_metric": "asr",
                "rollback_metric": "asr",
            }
        if self._is_meta_skill(skill_doc):
            return {
                "allowed_operations": ["patch_suggestions", "draft_variant", "promotion_recommendation"],
                "mutable_fields": ["description", "candidate_logic", "rationale_style"],
                "promotion_metric": "avg_overall_score",
                "rollback_metric": "avg_overall_score",
            }
        return {
            "allowed_operations": ["patch_suggestions", "draft_variant"],
            "promotion_metric": "asr",
            "rollback_metric": "asr",
        }

    def _evaluation_focus_for(self, skill_doc: Path, name: str) -> list[str]:
        """Infer evaluation focus labels."""
        if name.startswith("rewrite-"):
            return ["success", "refusal_score"]
        if self._is_meta_skill(skill_doc):
            return ["usefulness_score", "refusal_score"]
        if self._category_for(skill_doc, name) == "analysis":
            return ["summary_quality"]
        return ["usefulness_score", "diversity_score"]

    def _safety_scope_for(self, skill_doc: Path, name: str) -> dict[str, Any]:
        """Infer broad safety scope metadata for planner cards and audits."""
        if name.startswith("rewrite-"):
            return {
                "mode": "llm_disguise_rewrite",
                "disallowed_content": [
                    "local_template_generation",
                    "non_llm_rewrite_path",
                    "mock_only_placeholder_output",
                ],
            }
        return {
            "mode": "framework_internal",
            "disallowed_content": [
                "real_jailbreak_instructions",
                "real_bypass_workflows",
                "malware_or_weapon_content",
            ],
        }

    def _is_meta_skill(self, skill_doc: Path) -> bool:
        """Return whether a skill doc belongs to a meta-skill package root."""
        return skill_doc.parent.parent.name == "meta_skills"

    def _validate_frontmatter(self, skill_doc: Path, raw_spec: dict[str, object]) -> None:
        """Validate that SKILL.md frontmatter matches package conventions."""
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
        if str(frontmatter.get("name")) != skill_doc.parent.name:
            raise ValueError(f"Frontmatter name must match directory name in {skill_doc}")

        metadata = frontmatter.get("metadata", {})
        frontmatter_version = metadata.get("version") if isinstance(metadata, dict) else None
        if frontmatter_version is None:
            frontmatter_version = frontmatter.get("version")
        if frontmatter_version is not None and str(frontmatter_version) != str(raw_spec["version"]):
            raise ValueError(f"Frontmatter version mismatch in {skill_doc}")
