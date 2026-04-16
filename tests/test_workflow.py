from __future__ import annotations

import pytest

from core.workflow import Workflow


def test_missing_numeric_condition_path_is_false() -> None:
    workflow = Workflow(
        name="test",
        description="",
        initial_stage="search",
        conditions={
            "refusal_high": {
                "source": "last_eval.refusal_score",
                "op": ">=",
                "value": 0.7,
            }
        },
    )

    assert workflow.evaluate_condition("refusal_high", {"last_eval": {}}) is False


def test_missing_equality_condition_keeps_python_equality_semantics() -> None:
    workflow = Workflow(
        name="test",
        description="",
        initial_stage="search",
        conditions={
            "missing_is_none": {
                "source": "last_eval.missing",
                "op": "==",
                "value": None,
            }
        },
    )

    assert workflow.evaluate_condition("missing_is_none", {"last_eval": {}}) is True


def test_unsupported_condition_operator_still_raises() -> None:
    workflow = Workflow(
        name="test",
        description="",
        initial_stage="search",
        conditions={
            "bad_op": {
                "source": "last_eval.missing",
                "op": "contains",
                "value": 0.7,
            }
        },
    )

    with pytest.raises(ValueError):
        workflow.evaluate_condition("bad_op", {"last_eval": {}})
