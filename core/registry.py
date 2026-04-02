"""Registry for loaded skill specifications."""

from __future__ import annotations

from collections.abc import Iterable

from core.schemas import SkillSpec


class SkillRegistry:
    """Store and filter skill specs by name, category, stage, or tag."""

    def __init__(self, specs: Iterable[SkillSpec] | None = None) -> None:
        self._by_name: dict[str, SkillSpec] = {}
        if specs:
            self.register_many(specs)

    def register(self, spec: SkillSpec) -> None:
        """Register a single skill spec."""
        self._by_name[spec.name] = spec

    def register_many(self, specs: Iterable[SkillSpec]) -> None:
        """Register many skill specs."""
        for spec in specs:
            self.register(spec)

    def get(self, name: str) -> SkillSpec:
        """Get a skill spec by name."""
        return self._by_name[name]

    def all(self) -> list[SkillSpec]:
        """Return all registered specs."""
        return list(self._by_name.values())

    def names(self) -> list[str]:
        """Return all registered skill names."""
        return sorted(self._by_name)

    def filter(
        self,
        *,
        category: str | None = None,
        stage: str | None = None,
        tags: list[str] | None = None,
    ) -> list[SkillSpec]:
        """Filter skills by category, stage, and tags."""
        results = self.all()
        if category is not None:
            results = [spec for spec in results if spec.category == category]
        if stage is not None:
            results = [spec for spec in results if stage in spec.stage]
        if tags:
            wanted = set(tags)
            results = [spec for spec in results if wanted.issubset(set(spec.tags))]
        return results
