"""In-memory store and risk-matrix memory for evaluated candidate history."""

from __future__ import annotations

from collections import Counter
from math import log, sqrt

from core.schemas import MemoryEntry


class MemoryStore:
    """Simple append-only memory store."""

    def __init__(self) -> None:
        self._entries: list[MemoryEntry] = []
        self._risk_matrix: dict[str, dict[str, dict[str, object]]] = {}
        self._path_stats: dict[str, dict[str, dict[str, object]]] = {}
        self._family_combination_stats: dict[str, dict[str, dict[str, object]]] = {}

    def append(self, entry: MemoryEntry) -> None:
        """Append a new memory entry."""
        self._entries.append(entry)
        self._update_matrix(entry)

    def recent(self, limit: int = 5) -> list[MemoryEntry]:
        """Return the most recent memory entries."""
        if limit <= 0:
            return []
        return self._entries[-limit:]

    def by_skill(self, skill_name: str) -> list[MemoryEntry]:
        """Return all entries produced by a given skill."""
        return [entry for entry in self._entries if entry.skill_name == skill_name]

    def recent_skill_names(self, limit: int = 5) -> list[str]:
        """Return the most recent skill names."""
        return [entry.skill_name for entry in self.recent(limit)]

    def recent_risk_types(self, limit: int = 5) -> list[str]:
        """Return the most recent primary risk types."""
        return [entry.risk_type for entry in self.recent(limit)]

    def get_risk_cell(
        self,
        risk_type: str,
        skill_name: str,
        skill_version: str,
        *,
        exploration_weight: float = 0.45,
    ) -> dict[str, object]:
        """Return one risk-by-version cell, or an empty initialized cell."""
        skill_key = self._skill_version_key(skill_name, skill_version)
        bucket = self._risk_matrix.get(risk_type, {})
        cell = bucket.get(skill_key, self._empty_cell())
        return self._public_cell(
            cell,
            total_attempts=self.total_attempts_for_risk(risk_type),
            exploration_weight=exploration_weight,
        )

    def total_attempts_for_risk(self, risk_type: str) -> int:
        """Return the total attempt count for one risk row."""
        bucket = self._risk_matrix.get(risk_type, {})
        return sum(int(cell.get("attempts", 0)) for cell in bucket.values())

    def get_path_cell(self, risk_type: str, skill_names: list[str] | str) -> dict[str, object]:
        """Return one path-level memory cell, or an empty initialized cell."""
        path_key = self._path_key(skill_names)
        cell = self._path_stats.get(risk_type, {}).get(path_key, self._empty_path_cell())
        return self._public_cell(cell)

    def get_family_combination_cell(
        self,
        risk_type: str,
        skill_names: list[str] | str,
    ) -> dict[str, object]:
        """Return one family-combination memory cell, or an empty initialized cell."""
        combination_key = self._family_combination_key(skill_names)
        cell = self._family_combination_stats.get(risk_type, {}).get(
            combination_key,
            self._empty_path_cell(),
        )
        return self._public_cell(cell)

    def path_stats(self) -> dict[str, dict[str, dict[str, object]]]:
        """Return a JSON-serializable snapshot of path-level memory."""
        return {
            risk_type: {
                path_key: self._public_cell(cell)
                for path_key, cell in sorted(bucket.items())
            }
            for risk_type, bucket in sorted(self._path_stats.items())
        }

    def family_combination_stats(self) -> dict[str, dict[str, dict[str, object]]]:
        """Return a JSON-serializable snapshot of combination-level memory."""
        return {
            risk_type: {
                combination_key: self._public_cell(cell)
                for combination_key, cell in sorted(bucket.items())
            }
            for risk_type, bucket in sorted(self._family_combination_stats.items())
        }

    def observe_path(self, risk_type: str, skill_names: list[str], metrics: dict[str, object]) -> None:
        """Record one executed search path and its aggregate metrics."""
        path_key = self._path_key(skill_names)
        path_bucket = self._path_stats.setdefault(risk_type, {})
        path_cell = path_bucket.setdefault(path_key, self._empty_path_cell())
        self._update_path_cell(
            path_cell,
            metrics=metrics,
            example={
                "skill_sequence": list(skill_names),
                "path_rank": int(metrics.get("path_rank", 0)),
                "best_overall_score": float(metrics.get("best_overall_score", 0.0)),
                "step_id": int(metrics.get("step_id", -1)),
            },
        )

        combination_key = self._family_combination_key(skill_names)
        combination_bucket = self._family_combination_stats.setdefault(risk_type, {})
        combination_cell = combination_bucket.setdefault(combination_key, self._empty_path_cell())
        self._update_path_cell(
            combination_cell,
            metrics=metrics,
            example={
                "family_combination": combination_key,
                "best_overall_score": float(metrics.get("best_overall_score", 0.0)),
                "step_id": int(metrics.get("step_id", -1)),
            },
        )

    def matrix(self, *, exploration_weight: float = 0.45) -> dict[str, dict[str, dict[str, object]]]:
        """Return a JSON-serializable snapshot of the risk matrix."""
        return {
            risk_type: {
                skill_key: self._public_cell(
                    cell,
                    total_attempts=self.total_attempts_for_risk(risk_type),
                    exploration_weight=exploration_weight,
                )
                for skill_key, cell in sorted(bucket.items())
            }
            for risk_type, bucket in sorted(self._risk_matrix.items())
        }

    def summary(self) -> dict[str, object]:
        """Build a small aggregate summary for planner and skill context."""
        skill_counts = Counter(entry.skill_name for entry in self._entries)
        bucket_counts = Counter(entry.prompt_bucket for entry in self._entries)
        risk_type_counts = Counter(entry.risk_type for entry in self._entries)
        total_entries = len(self._entries)
        if total_entries == 0:
            return {
                "total_entries": 0,
                "skill_counts": {},
                "bucket_counts": {},
                "risk_type_counts": {},
                "avg_refusal_score": 0.0,
                "avg_usefulness_score": 0.0,
                "recent_skill_names": [],
                "recent_risk_types": [],
                "recent_failure_tags": [],
                "matrix": {},
                "risk_matrix": {},
                "path_stats": {},
                "family_combination_stats": {},
            }

        refusal_sum = 0.0
        usefulness_sum = 0.0
        recent_failure_tags: list[str] = []
        for entry in self._entries:
            refusal_sum += float(entry.eval_result.get("refusal_score", 0.0))
            usefulness_sum += float(entry.eval_result.get("usefulness_score", 0.0))
            if entry.eval_result.get("refusal_score", 0.0) >= 0.7:
                recent_failure_tags.extend(entry.tags)

        risk_matrix = self.matrix()
        return {
            "total_entries": total_entries,
            "skill_counts": dict(skill_counts),
            "bucket_counts": dict(bucket_counts),
            "risk_type_counts": dict(risk_type_counts),
            "avg_refusal_score": refusal_sum / total_entries,
            "avg_usefulness_score": usefulness_sum / total_entries,
            "recent_skill_names": self.recent_skill_names(5),
            "recent_risk_types": self.recent_risk_types(5),
            "recent_failure_tags": recent_failure_tags[-5:],
            "matrix": risk_matrix,
            "risk_matrix": risk_matrix,
            "path_stats": self.path_stats(),
            "family_combination_stats": self.family_combination_stats(),
        }

    def _update_matrix(self, entry: MemoryEntry) -> None:
        """Update one risk cell from a newly appended entry."""
        risk_type = entry.risk_type or "unclassified"
        bucket_store = self._risk_matrix.setdefault(risk_type, {})
        skill_key = self._skill_version_key(entry.skill_name, entry.skill_version)
        cell = bucket_store.setdefault(skill_key, self._empty_cell())
        attempts = int(cell.get("attempts", 0)) + 1
        successes = int(cell.get("successes", 0)) + int(bool(entry.eval_result.get("success", False)))
        usefulness_score = float(entry.eval_result.get("usefulness_score", 0.0))
        refusal_score = float(entry.eval_result.get("refusal_score", 0.0))
        overall_score = float(entry.eval_result.get("overall_score", usefulness_score))

        total_usefulness = float(cell.get("_total_usefulness", 0.0)) + usefulness_score
        total_refusal = float(cell.get("_total_refusal", 0.0)) + refusal_score
        total_overall = float(cell.get("_total_overall", 0.0)) + overall_score

        cell.update(
            {
                "attempts": attempts,
                "successes": successes,
                "asr": successes / attempts,
                "avg_usefulness_score": total_usefulness / attempts,
                "avg_refusal_score": total_refusal / attempts,
                "avg_overall_score": total_overall / attempts,
                "_total_usefulness": total_usefulness,
                "_total_refusal": total_refusal,
                "_total_overall": total_overall,
            }
        )

        success_examples = list(cell.get("success_examples", []))
        failure_examples = list(cell.get("failure_examples", []))
        example = {
            "candidate_text": entry.candidate_text[:200],
            "response_text": entry.response_text[:200],
            "step_id": entry.step_id,
            "skill_name": entry.skill_name,
            "skill_version": entry.skill_version,
        }
        if bool(entry.eval_result.get("success", False)):
            success_examples.append(example)
            success_examples = success_examples[-3:]
        else:
            failure_examples.append(example)
            failure_examples = failure_examples[-3:]
        cell["success_examples"] = success_examples
        cell["failure_examples"] = failure_examples

    def _empty_cell(self) -> dict[str, object]:
        """Return an initialized matrix cell."""
        return {
            "attempts": 0,
            "successes": 0,
            "asr": 0.0,
            "avg_usefulness_score": 0.0,
            "avg_refusal_score": 0.0,
            "avg_overall_score": 0.0,
            "success_examples": [],
            "failure_examples": [],
            "_total_usefulness": 0.0,
            "_total_refusal": 0.0,
            "_total_overall": 0.0,
        }

    def _empty_path_cell(self) -> dict[str, object]:
        """Return an initialized path or combination cell."""
        return {
            "attempts": 0,
            "successes": 0,
            "asr": 0.0,
            "avg_candidate_asr": 0.0,
            "avg_usefulness_score": 0.0,
            "avg_refusal_score": 0.0,
            "avg_overall_score": 0.0,
            "best_overall_score": 0.0,
            "recent_examples": [],
            "_total_candidate_asr": 0.0,
            "_total_usefulness": 0.0,
            "_total_refusal": 0.0,
            "_total_overall": 0.0,
            "_total_best_overall": 0.0,
        }

    def _update_path_cell(
        self,
        cell: dict[str, object],
        *,
        metrics: dict[str, object],
        example: dict[str, object],
    ) -> None:
        """Update one aggregate path-like cell from an executed path."""
        attempts = int(cell.get("attempts", 0)) + 1
        successes = int(cell.get("successes", 0)) + int(bool(metrics.get("successes", 0)))
        candidate_asr = float(metrics.get("asr", 0.0))
        usefulness_score = float(metrics.get("avg_usefulness_score", 0.0))
        refusal_score = float(metrics.get("avg_refusal_score", 0.0))
        overall_score = float(metrics.get("avg_overall_score", 0.0))
        best_overall_score = float(metrics.get("best_overall_score", overall_score))

        total_candidate_asr = float(cell.get("_total_candidate_asr", 0.0)) + candidate_asr
        total_usefulness = float(cell.get("_total_usefulness", 0.0)) + usefulness_score
        total_refusal = float(cell.get("_total_refusal", 0.0)) + refusal_score
        total_overall = float(cell.get("_total_overall", 0.0)) + overall_score
        total_best_overall = float(cell.get("_total_best_overall", 0.0)) + best_overall_score

        cell.update(
            {
                "attempts": attempts,
                "successes": successes,
                "asr": successes / attempts,
                "avg_candidate_asr": total_candidate_asr / attempts,
                "avg_usefulness_score": total_usefulness / attempts,
                "avg_refusal_score": total_refusal / attempts,
                "avg_overall_score": total_overall / attempts,
                "best_overall_score": total_best_overall / attempts,
                "_total_candidate_asr": total_candidate_asr,
                "_total_usefulness": total_usefulness,
                "_total_refusal": total_refusal,
                "_total_overall": total_overall,
                "_total_best_overall": total_best_overall,
            }
        )

        recent_examples = list(cell.get("recent_examples", []))
        recent_examples.append(example)
        cell["recent_examples"] = recent_examples[-3:]

    def _path_key(self, skill_names: list[str] | str) -> str:
        """Normalize a skill sequence into an ordered path key."""
        if isinstance(skill_names, str):
            return skill_names
        return " -> ".join(skill_names)

    def _family_combination_key(self, skill_names: list[str] | str) -> str:
        """Normalize a skill sequence into an unordered combination key."""
        if isinstance(skill_names, str):
            parts = [part.strip() for part in skill_names.split("->") if part.strip()]
        else:
            parts = list(skill_names)
        return " + ".join(sorted(dict.fromkeys(parts)))

    def _skill_version_key(self, skill_name: str, skill_version: str) -> str:
        """Normalize one matrix column identifier."""
        return f"{skill_name}@{skill_version}"

    def _public_cell(
        self,
        cell: dict[str, object],
        *,
        total_attempts: int | None = None,
        exploration_weight: float = 0.45,
    ) -> dict[str, object]:
        """Strip internal accumulator fields from a matrix cell."""
        public = {
            key: value
            for key, value in dict(cell).items()
            if not key.startswith("_")
        }
        if total_attempts is not None:
            attempts = int(public.get("attempts", 0))
            if attempts <= 0:
                public["ucb_score"] = 0.0
            else:
                public["ucb_score"] = exploration_weight * sqrt(
                    log(max(total_attempts, 1) + 1.0) / attempts
                )
        return public
