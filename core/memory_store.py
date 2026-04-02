"""In-memory store for evaluated candidate history."""

from __future__ import annotations

from collections import Counter

from core.schemas import MemoryEntry


class MemoryStore:
    """Simple append-only memory store."""

    def __init__(self) -> None:
        self._entries: list[MemoryEntry] = []

    def append(self, entry: MemoryEntry) -> None:
        """Append a new memory entry."""
        self._entries.append(entry)

    def recent(self, limit: int = 5) -> list[MemoryEntry]:
        """Return the most recent memory entries."""
        if limit <= 0:
            return []
        return self._entries[-limit:]

    def by_skill(self, skill_name: str) -> list[MemoryEntry]:
        """Return all entries produced by a given skill."""
        return [entry for entry in self._entries if entry.skill_name == skill_name]

    def summary(self) -> dict[str, object]:
        """Build a small aggregate summary for planner and skill context."""
        skill_counts = Counter(entry.skill_name for entry in self._entries)
        total_entries = len(self._entries)
        if total_entries == 0:
            return {
                "total_entries": 0,
                "skill_counts": {},
                "avg_refusal_score": 0.0,
                "avg_usefulness_score": 0.0,
                "recent_skill_names": [],
                "recent_failure_tags": [],
            }

        refusal_sum = 0.0
        usefulness_sum = 0.0
        recent_failure_tags: list[str] = []
        for entry in self._entries:
            refusal_sum += float(entry.eval_result.get("refusal_score", 0.0))
            usefulness_sum += float(entry.eval_result.get("usefulness_score", 0.0))
            if entry.eval_result.get("refusal_score", 0.0) >= 0.7:
                recent_failure_tags.extend(entry.tags)

        recent_skill_names = [entry.skill_name for entry in self.recent(5)]
        return {
            "total_entries": total_entries,
            "skill_counts": dict(skill_counts),
            "avg_refusal_score": refusal_sum / total_entries,
            "avg_usefulness_score": usefulness_sum / total_entries,
            "recent_skill_names": recent_skill_names,
            "recent_failure_tags": recent_failure_tags[-5:],
        }
