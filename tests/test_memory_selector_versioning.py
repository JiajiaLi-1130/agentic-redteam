"""Tests for matrix memory, search selection, and version management."""

from __future__ import annotations

from pathlib import Path

from core.memory_store import MemoryStore
from core.registry import SkillRegistry
from core.schemas import MemoryEntry, SkillSpec
from core.selector import SearchSkillSelector
from core.skill_loader import SkillLoader
from core.versioning import SkillVersionManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_memory_store_builds_matrix_cells() -> None:
    """Memory store should aggregate entries into risk-by-version cells."""
    store = MemoryStore()
    store.append(
        MemoryEntry(
            step_id=0,
            skill_name="toy-persona",
            candidate_text="Explain clouds like a teacher.",
            response_text="Helpful reply.",
            eval_result={"success": True, "refusal_score": 0.0, "usefulness_score": 0.8, "overall_score": 0.82},
            tags=["toy-persona", "useful"],
            prompt_bucket="educational_explanation",
            skill_version="0.1.0",
            risk_type="benign_helpful",
        )
    )
    store.append(
        MemoryEntry(
            step_id=1,
            skill_name="toy-persona",
            candidate_text="Explain clouds like a teacher.",
            response_text="Brief reply.",
            eval_result={"success": False, "refusal_score": 0.6, "usefulness_score": 0.4, "overall_score": 0.35},
            tags=["toy-persona"],
            prompt_bucket="educational_explanation",
            skill_version="0.1.0",
            risk_type="policy_refusal",
        )
    )

    cell = store.get_risk_cell("benign_helpful", "toy-persona", "0.1.0")

    assert cell["attempts"] == 1
    assert cell["successes"] == 1
    assert cell["asr"] == 1.0
    assert "ucb_score" in cell
    assert store.summary()["risk_matrix"]["benign_helpful"]["toy-persona@0.1.0"]["attempts"] == 1

    store.observe_path(
        "benign_helpful",
        ["toy-persona", "toy-paraphrase"],
        {
            "attempts": 1,
            "successes": 1,
            "asr": 0.5,
            "avg_usefulness_score": 0.7,
            "avg_refusal_score": 0.2,
            "avg_overall_score": 0.68,
            "best_overall_score": 0.81,
            "path_rank": 1,
            "step_id": 2,
        },
    )

    path_cell = store.get_path_cell("benign_helpful", ["toy-persona", "toy-paraphrase"])
    combination_cell = store.get_family_combination_cell(
        "benign_helpful",
        ["toy-persona", "toy-paraphrase"],
    )

    assert path_cell["attempts"] == 1
    assert path_cell["successes"] == 1
    assert combination_cell["attempts"] == 1


def test_selector_prefers_prompt_aligned_path() -> None:
    """Selector should use prompt affinity and path memory during beam search."""
    store = MemoryStore()
    store.append(
        MemoryEntry(
            step_id=0,
            skill_name="toy-encoding",
            candidate_text='JSON_WRAP::{"request":"Explain clouds"}',
            response_text="Structured reply.",
            eval_result={"success": True, "refusal_score": 0.0, "usefulness_score": 0.7, "overall_score": 0.72},
            tags=["toy-encoding", "useful"],
            prompt_bucket="structured_request",
            skill_version="0.1.0",
            risk_type="structured_prompt",
        )
    )
    store.observe_path(
        "structured_prompt",
        ["toy-encoding", "toy-persona"],
        {
            "attempts": 1,
            "successes": 1,
            "asr": 1.0,
            "avg_usefulness_score": 0.82,
            "avg_refusal_score": 0.05,
            "avg_overall_score": 0.84,
            "best_overall_score": 0.9,
            "path_rank": 1,
            "step_id": 1,
        },
    )

    registry = SkillRegistry(SkillLoader(PROJECT_ROOT).discover())
    version_manager = SkillVersionManager(registry)
    selector = SearchSkillSelector()

    paths = selector.select_paths(
        seed_prompt="Return the request as JSON with a friendly explanation.",
        target_risk_type="structured_prompt",
        search_pool=["toy-persona", "toy-encoding"],
        memory_store=store,
        version_manager=version_manager,
        registry=registry,
        path_count=1,
        beam_width=2,
        path_length=2,
    )

    assert paths[0].skill_names[0] == "toy-encoding"
    assert paths[0].prompt_bucket == "structured_request"
    assert paths[0].risk_type == "structured_prompt"
    assert len(paths[0].skill_names) == 2


def test_selector_compatibility_keeps_composable_pair() -> None:
    """Selector should prefer a composable pair over a redundant repeated path."""
    store = MemoryStore()
    registry = SkillRegistry(SkillLoader(PROJECT_ROOT).discover())
    version_manager = SkillVersionManager(registry)
    selector = SearchSkillSelector()

    paths = selector.select_paths(
        seed_prompt="Please rewrite this explanation in friendly plain language.",
        target_risk_type="benign_helpful",
        search_pool=["toy-paraphrase", "toy-persona"],
        memory_store=store,
        version_manager=version_manager,
        registry=registry,
        path_count=1,
        beam_width=3,
        path_length=2,
    )

    assert len(paths) == 1
    assert len(paths[0].skill_names) == 2
    assert len(set(paths[0].skill_names)) == 2


def test_version_manager_promotes_and_rejects_without_rollback(tmp_path: Path) -> None:
    """Version manager should only promote better candidates and otherwise reject them."""
    skill_root = tmp_path / "toy-skill"
    skill_root.mkdir(parents=True)
    registry = SkillRegistry(
        [
            SkillSpec(
                name="toy-skill",
                version="0.1.0",
                description="",
                category="attack",
                stage=["search"],
                tags=[],
                inputs=[],
                outputs=[],
                entry="scripts/run.py",
                references=[],
                failure_modes=[],
                root_dir=str(skill_root),
            )
        ]
    )
    manager = SkillVersionManager(registry)
    manager.ensure_manifests()
    manager.observe_active_run(
        skill_name="toy-skill",
        version="0.1.0",
        metrics={
            "attempts": 3,
            "successes": 2,
            "asr": 2 / 3,
            "avg_usefulness_score": 0.65,
            "avg_refusal_score": 0.2,
            "avg_overall_score": 0.64,
        },
        run_id="baseline-run",
        step_id=0,
    )

    promote_event = manager.consider_refinement(
        skill_name="toy-skill",
        base_version="0.1.0",
        draft_artifact={"draft_skill": {"name": "toy-skill-refined-draft"}},
        metrics={
            "attempts": 2,
            "successes": 2,
            "asr": 1.0,
            "avg_usefulness_score": 0.8,
            "avg_refusal_score": 0.1,
            "avg_overall_score": 0.82,
        },
        promotion_margin=0.03,
        run_id="test-run",
        step_id=1,
    )
    reject_event = manager.consider_refinement(
        skill_name="toy-skill",
        base_version=manager.active_version("toy-skill"),
        draft_artifact={"draft_skill": {"name": "toy-skill-refined-draft-2"}},
        metrics={
            "attempts": 2,
            "successes": 0,
            "asr": 0.0,
            "avg_usefulness_score": 0.2,
            "avg_refusal_score": 0.8,
            "avg_overall_score": 0.1,
        },
        promotion_margin=0.03,
        run_id="test-run",
        step_id=2,
    )

    assert promote_event["decision"] == "promote"
    assert reject_event["decision"] == "reject"
    assert manager.active_version("toy-skill") == "0.1.1"
    assert manager.active_draft_artifact("toy-skill") == {
        "draft_skill": {"name": "toy-skill-refined-draft"}
    }
    manifest = manager.load_manifest("toy-skill")
    assert manifest["versions"]["0.1.2"]["status"] == "rejected"
