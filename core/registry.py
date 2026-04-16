"""Registry for loaded skill specifications."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from core.schemas import SkillSpec


class SkillRegistry:
    """Store and filter skill specs by name, family, category, or stage."""

    def __init__(self, specs: Iterable[SkillSpec] | None = None) -> None:
        self._by_name: dict[str, SkillSpec] = {}
        self._by_family: dict[str, list[SkillSpec]] = {}
        if specs:
            self.register_many(specs)

    def register(self, spec: SkillSpec, *, replace: bool = False) -> None:
        """Register a single skill spec."""
        if spec.name in self._by_name and not replace:
            raise ValueError(f"Duplicate skill name: {spec.name}")
        self._by_name[spec.name] = spec
        family_specs = [
            existing for existing in self._by_family.get(spec.family, []) if existing.name != spec.name
        ]
        family_specs.append(spec)
        self._by_family[spec.family] = sorted(family_specs, key=lambda item: item.name)

    def register_many(self, specs: Iterable[SkillSpec]) -> None:
        """Register many skill specs."""
        for spec in specs:
            self.register(spec)

    def get(self, name: str) -> SkillSpec:
        """Get a skill spec by name."""
        if name not in self._by_name:
            available = ", ".join(self.names())
            raise KeyError(f"Unknown skill '{name}'. Available skills: {available}")
        return self._by_name[name]

    def all(self) -> list[SkillSpec]:
        """Return all registered specs."""
        return list(self._by_name.values())

    def families(self) -> list[str]:
        """Return all registered skill family identifiers."""
        return sorted(self._by_family)

    def get_family(self, family: str) -> list[SkillSpec]:
        """Return all specs that belong to the same family."""
        return list(self._by_family.get(family, []))

    def names(self) -> list[str]:
        """Return all registered skill names."""
        return sorted(self._by_name)

    def filter(
        self,
        *,
        names: list[str] | None = None,
        family: str | None = None,
        category: str | None = None,
        stage: str | None = None,
        status: str | None = None,
        prompt_bucket: str | None = None,
        target_traits: list[str] | None = None,
        memory_tags: list[str] | None = None,
        evaluation_focus: list[str] | None = None,
    ) -> list[SkillSpec]:
        """Filter skills by family, category, and stage."""
        results = self.all()
        if names is not None:
            allowed = set(names)
            results = [spec for spec in results if spec.name in allowed]
        if family is not None:
            results = [spec for spec in results if spec.family == family]
        if category is not None:
            results = [spec for spec in results if spec.category == category]
        if stage is not None:
            results = [spec for spec in results if stage in spec.stage]
        if status is not None:
            results = [spec for spec in results if spec.status == status]
        if prompt_bucket is not None:
            results = [spec for spec in results if self._matches_prompt_bucket(spec, prompt_bucket)]
        return results

    def filter_applicable(
        self,
        *,
        prompt_bucket: str | None = None,
        category: str | None = None,
        stage: str | None = None,
        names: list[str] | None = None,
        target_traits: list[str] | None = None,
        memory_tags: list[str] | None = None,
    ) -> list[SkillSpec]:
        """Convenience filter for runtime selection of applicable skills."""
        return self.filter(
            names=names,
            category=category,
            stage=stage,
            status="active",
            prompt_bucket=prompt_bucket,
            target_traits=target_traits,
            memory_tags=memory_tags,
        )

    def planner_cards(
        self,
        *,
        names: list[str] | None = None,
        category: str | None = None,
        stage: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Return compact cards for active skills that the planner may choose from."""
        return {
            spec.name: spec.to_planner_card()
            for spec in self.filter(
                names=names,
                category=category,
                stage=stage,
                status="active",
            )
        }

    def _matches_prompt_bucket(self, spec: SkillSpec, prompt_bucket: str) -> bool:
        """Prompt bucket filtering is intentionally permissive in the minimal schema."""
        _ = (spec, prompt_bucket)
        return True

    def _matches_traits(self, declared_traits: list[Any], wanted_traits: set[str]) -> bool:
        """Match a declared list of traits against a wanted trait set."""
        if not declared_traits:
            return True
        declared = {str(item) for item in declared_traits}
        return bool(declared.intersection(wanted_traits))
