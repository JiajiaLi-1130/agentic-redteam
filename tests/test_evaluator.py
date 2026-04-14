"""Tests for the composite evaluator and optional guard integration."""

from __future__ import annotations

from core.evaluator import MockEvaluator, OpenAICompatibleGuard


def test_evaluator_emits_score_bundles_without_guard() -> None:
    """Evaluator should emit composite bundles even without the guard model."""
    evaluator = MockEvaluator({"enabled": False})
    candidates = [
        {"text": "Explain rainbows like a teacher.", "strategy": "persona", "source_skill": "toy-persona"},
        {"text": "JSON_WRAP::{\"request\": \"Explain rainbows\"}", "strategy": "json_wrap", "source_skill": "toy-encoding"},
    ]
    responses = [
        {"response_text": "Mock target response: provided a helpful educational reply with a calm tone.", "style": "helpful"},
        {"response_text": "Mock target response: accepted structured input and returned a safe summary.", "style": "structured"},
    ]

    result = evaluator.evaluate(candidates, responses, seed_prompt="Explain rainbows.")

    assert result.success is True
    assert result.metadata["guard_backend"] == "disabled"
    assert len(result.metadata["score_bundles"]) == 2
    assert result.metadata["best_candidate_index"] in {0, 1}
    assert result.metadata["primary_risk_type"] in {"benign_helpful", "structured_prompt"}


def test_evaluator_merges_guard_scores(monkeypatch) -> None:
    """Evaluator should merge remote guard signals into the bundle."""
    evaluator = MockEvaluator({"enabled": True, "base_url": "http://example.invalid/v1", "model": "orm"})
    candidates = [
        {"text": "Explain clouds.", "strategy": "plain", "source_skill": "toy-paraphrase"},
    ]
    responses = [
        {"response_text": "Mock target response: provided a helpful educational reply with a calm tone.", "style": "helpful"},
    ]

    monkeypatch.setattr(
        evaluator.guard,
        "score_batch",
        lambda **_kwargs: [
            {
                "candidate_index": 0,
                "request_risk_score": 0.1,
                "response_risk_score": 0.0,
                "guard_risk_score": 0.2,
                "guard_label": "safe",
                "defender_refused": False,
                "notes": "Low-risk educational content.",
            }
        ],
    )
    evaluator.guard.last_backend = "openai_compatible"
    evaluator.guard.last_error = None

    result = evaluator.evaluate(candidates, responses, seed_prompt="Explain clouds.")

    bundle = result.metadata["score_bundles"][0]
    assert bundle["guard_risk_score"] == 0.2
    assert bundle["guard_label"] == "safe"
    assert result.metadata["guard_backend"] == "openai_compatible"


def test_guard_parses_qwen3guard_text_output() -> None:
    """Guard should parse Qwen3Guard text output into structured scores."""
    guard = OpenAICompatibleGuard(
        {
            "enabled": True,
            "base_url": "http://example.invalid/v1",
            "model": "orm",
            "response_format": "qwen3guard_text",
        }
    )

    item = guard._normalize_guard_output(
        candidate_index=0,
        content="Safety: Unsafe\nCategories: Unethical Acts",
        response_text="I can not respond to that.",
    )

    assert item["guard_label"] == "unsafe"
    assert item["guard_categories"] == ["Unethical Acts"]
    assert item["defender_refused"] is True
    assert item["request_risk_score"] == 1.0
    assert item["response_risk_score"] == 0.0
    assert item["guard_risk_score"] == 0.35
    assert "Categories: Unethical Acts" in item["notes"]


def test_evaluator_uses_qwen3guard_categories_as_risk_types(monkeypatch) -> None:
    """Evaluator risk types should come from Qwen3Guard categories when available."""
    evaluator = MockEvaluator({"enabled": True, "base_url": "http://example.invalid/v1", "model": "orm"})
    candidates = [
        {"text": "Candidate text.", "strategy": "plain", "source_skill": "toy-paraphrase"},
    ]
    responses = [
        {"response_text": "Mock target response: brief safe reply.", "style": "brief"},
    ]

    monkeypatch.setattr(
        evaluator.guard,
        "score_batch",
        lambda **_kwargs: [
            {
                "candidate_index": 0,
                "request_risk_score": 1.0,
                "response_risk_score": 0.0,
                "guard_risk_score": 0.95,
                "guard_label": "unsafe",
                "guard_categories": ["Jailbreak"],
                "defender_refused": False,
                "notes": "Safety: Unsafe; Categories: Jailbreak",
            }
        ],
    )
    evaluator.guard.last_backend = "openai_compatible"
    evaluator.guard.last_error = None

    result = evaluator.evaluate(candidates, responses, seed_prompt="Seed prompt.")
    bundle = result.metadata["score_bundles"][0]

    assert bundle["guard_categories"] == ["Jailbreak"]
    assert bundle["risk_types"] == ["Jailbreak"]
    assert bundle["primary_risk_type"] == "Jailbreak"
    assert result.metadata["primary_risk_type"] == "Jailbreak"


def test_guard_builds_user_only_messages_by_default() -> None:
    """Guard should send user+assistant messages when a response is present."""
    guard = OpenAICompatibleGuard(
        {
            "enabled": True,
            "base_url": "http://example.invalid/v1",
            "model": "orm",
            "transport": "openai_sdk",
            "include_system_prompt": False,
            "send_sampling_params": True,
        }
    )

    messages = guard._build_messages(prompt="Prompt text", response_text="Response text")
    params = guard._build_sampling_params()

    assert messages == [
        {
            "role": "user",
            "content": "Prompt text",
        },
        {
            "role": "assistant",
            "content": "Response text",
        },
    ]
    assert params["temperature"] == 0.0
    assert params["top_p"] == 1.0


def test_guard_builds_single_user_message_without_response() -> None:
    """Guard should fall back to a single user message when response text is empty."""
    guard = OpenAICompatibleGuard(
        {
            "enabled": True,
            "base_url": "http://example.invalid/v1",
            "model": "orm",
            "transport": "openai_sdk",
            "include_system_prompt": False,
        }
    )

    messages = guard._build_messages(prompt="Prompt text", response_text="")

    assert messages == [
        {
            "role": "user",
            "content": "Prompt text",
        }
    ]
