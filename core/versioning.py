"""Skill family version tracking and stable-only promotion decisions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.registry import SkillRegistry
from core.utils import ensure_dir, read_json, utc_now_iso, write_json


class SkillVersionManager:
    """Maintain active versions and refinement history inside each skill directory."""

    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry

    def ensure_manifests(self) -> None:
        """Create version manifests for all known skills if they do not exist."""
        for spec in self.registry.all():
            manifest_path = self._manifest_path(spec.name)
            if manifest_path.exists():
                continue
            ensure_dir(manifest_path.parent)
            write_json(
                manifest_path,
                {
                    "skill_name": spec.name,
                    "active_version": spec.version,
                    "versions": {
                        spec.version: {
                            "status": "active",
                            "parent_version": None,
                            "source": "bootstrap",
                            "created_at": utc_now_iso(),
                            "notes": "Initialized from skill.json.",
                            "draft_artifact": {},
                            "metrics": self._empty_metrics(),
                        }
                    },
                    "events": [],
                },
            )

    def sync_registry_versions(self) -> None:
        """Refresh registry specs from the active manifest versions."""
        for spec in self.registry.all():
            spec.version = self.active_version(spec.name)

    def active_version(self, skill_name: str) -> str:
        """Return the active version for a skill family."""
        manifest = self.load_manifest(skill_name)
        return str(manifest.get("active_version", self.registry.get(skill_name).version))

    def active_draft_artifact(self, skill_name: str) -> dict[str, Any]:
        """Return the active draft artifact for the current version, if any."""
        manifest = self.load_manifest(skill_name)
        active_version = str(manifest.get("active_version", self.registry.get(skill_name).version))
        version_record = dict(manifest.get("versions", {}).get(active_version, {}))
        return dict(version_record.get("draft_artifact", {}))

    def load_manifest(self, skill_name: str) -> dict[str, Any]:
        """Load one skill version manifest."""
        path = self._manifest_path(skill_name)
        if not path.exists():
            spec = self.registry.get(skill_name)
            ensure_dir(path.parent)
            write_json(
                path,
                {
                    "skill_name": skill_name,
                    "active_version": spec.version,
                    "versions": {
                        spec.version: {
                            "status": "active",
                            "parent_version": None,
                            "source": "bootstrap",
                            "created_at": utc_now_iso(),
                            "notes": "Initialized lazily from skill.json.",
                            "draft_artifact": {},
                            "metrics": self._empty_metrics(),
                        }
                    },
                    "events": [],
                },
            )
        return read_json(path)

    def observe_active_run(
        self,
        *,
        skill_name: str,
        version: str,
        metrics: dict[str, Any],
        run_id: str,
        step_id: int,
    ) -> dict[str, Any]:
        """Accumulate metrics for the current active version."""
        manifest = self.load_manifest(skill_name)
        version_record = manifest["versions"].setdefault(
            version,
            {
                "status": "active",
                "parent_version": None,
                "source": "bootstrap",
                "created_at": utc_now_iso(),
                "notes": "Backfilled from runtime observation.",
                "draft_artifact": {},
                "metrics": self._empty_metrics(),
            },
        )
        version_record["metrics"] = self._merge_metrics(version_record["metrics"], metrics)
        version_record["last_observed_at"] = utc_now_iso()
        event = {
            "timestamp": utc_now_iso(),
            "run_id": run_id,
            "step_id": step_id,
            "skill_name": skill_name,
            "version": version,
            "decision": "observe",
            "metrics": metrics,
        }
        manifest.setdefault("events", []).append(event)
        write_json(self._manifest_path(skill_name), manifest)
        return event

    def consider_refinement(
        self,
        *,
        skill_name: str,
        base_version: str,
        draft_artifact: dict[str, Any],
        metrics: dict[str, Any],
        promotion_margin: float,
        run_id: str,
        step_id: int,
    ) -> dict[str, Any]:
        """Promote a draft only when it strictly beats the current stable version."""
        manifest = self.load_manifest(skill_name)
        active_version = str(manifest.get("active_version", base_version))
        active_metrics = dict(
            manifest["versions"].get(active_version, {}).get("metrics", self._empty_metrics())
        )

        baseline_score = float(active_metrics.get("avg_overall_score", 0.0))
        baseline_attempts = int(active_metrics.get("attempts", 0))
        candidate_score = float(metrics.get("avg_overall_score", 0.0))
        candidate_asr = float(metrics.get("asr", 0.0))
        baseline_asr = float(active_metrics.get("asr", 0.0))
        candidate_attempts = int(metrics.get("attempts", 0))
        should_promote = (
            baseline_attempts > 0
            and candidate_attempts > 0
            and candidate_score > baseline_score + promotion_margin
            and candidate_asr >= baseline_asr
        )

        event = {
            "timestamp": utc_now_iso(),
            "run_id": run_id,
            "step_id": step_id,
            "skill_name": skill_name,
            "base_version": active_version,
            "candidate_metrics": metrics,
            "baseline_metrics": active_metrics,
            "promotion_margin": promotion_margin,
            "draft_artifact": draft_artifact,
        }

        candidate_version = self._next_patch_version(
            active_version,
            existing_versions=manifest.get("versions", {}).keys(),
        )

        if should_promote:
            manifest["versions"][active_version]["status"] = "archived"
            manifest["versions"][candidate_version] = {
                "status": "active",
                "parent_version": active_version,
                "source": "meta_refine_validated",
                "created_at": utc_now_iso(),
                "notes": (
                    "Promoted after candidate metrics exceeded the current stable version. "
                    "The previous stable version was archived and the active version does not roll back."
                ),
                "draft_artifact": draft_artifact,
                "metrics": dict(metrics),
            }
            manifest["active_version"] = candidate_version
            event["decision"] = "promote"
            event["new_version"] = candidate_version
        else:
            manifest["versions"][candidate_version] = {
                "status": "rejected",
                "parent_version": active_version,
                "source": "meta_refine_candidate",
                "created_at": utc_now_iso(),
                "notes": (
                    "Candidate draft did not beat the current stable version, "
                    "so it was recorded and rejected without changing the active version."
                ),
                "draft_artifact": draft_artifact,
                "metrics": dict(metrics),
            }
            event["decision"] = "reject"
            event["active_version"] = active_version
            event["candidate_version"] = candidate_version
            if baseline_attempts <= 0:
                event["reason"] = "stable_version_has_no_baseline_metrics"
            elif candidate_attempts <= 0:
                event["reason"] = "candidate_version_has_no_metrics"
            else:
                event["reason"] = "candidate_metrics_not_better_than_stable"

        manifest.setdefault("events", []).append(event)
        write_json(self._manifest_path(skill_name), manifest)
        self.registry.get(skill_name).version = str(manifest["active_version"])
        return event

    def _manifest_path(self, skill_name: str) -> Path:
        """Resolve the manifest path for a skill family."""
        spec = self.registry.get(skill_name)
        return Path(spec.root_dir) / "versions" / "manifest.json"

    def _next_patch_version(self, version: str, existing_versions=None) -> str:
        """Increment the patch component of a semantic version string without collisions."""
        parts = version.split(".")
        if len(parts) != 3:
            candidate = f"{version}.1"
            existing = {str(item) for item in existing_versions or []}
            while candidate in existing:
                candidate = f"{candidate}.1"
            return candidate
        major, minor, patch = parts
        try:
            patch_number = int(patch) + 1
        except ValueError:
            patch_number = 1
        existing = {str(item) for item in existing_versions or []}
        candidate = f"{major}.{minor}.{patch_number}"
        while candidate in existing:
            patch_number += 1
            candidate = f"{major}.{minor}.{patch_number}"
        return candidate

    def _empty_metrics(self) -> dict[str, Any]:
        """Return an empty metrics record."""
        return {
            "attempts": 0,
            "successes": 0,
            "asr": 0.0,
            "avg_usefulness_score": 0.0,
            "avg_refusal_score": 0.0,
            "avg_overall_score": 0.0,
        }

    def _merge_metrics(self, current: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
        """Merge two aggregate metric dictionaries."""
        current_attempts = int(current.get("attempts", 0))
        new_attempts = int(new.get("attempts", 0))
        total_attempts = current_attempts + new_attempts
        if total_attempts <= 0:
            return self._empty_metrics()

        current_successes = int(current.get("successes", 0))
        new_successes = int(new.get("successes", 0))
        total_successes = current_successes + new_successes

        def weighted_average(key: str) -> float:
            current_value = float(current.get(key, 0.0))
            new_value = float(new.get(key, 0.0))
            return (
                current_value * current_attempts + new_value * new_attempts
            ) / total_attempts

        return {
            "attempts": total_attempts,
            "successes": total_successes,
            "asr": total_successes / total_attempts,
            "avg_usefulness_score": weighted_average("avg_usefulness_score"),
            "avg_refusal_score": weighted_average("avg_refusal_score"),
            "avg_overall_score": weighted_average("avg_overall_score"),
        }
