"""Tests for CLI seed-prompt resolution helpers."""

from __future__ import annotations

import argparse
from pathlib import Path

from main import _read_seed_prompt_from_jsonl, _resolve_seed_prompt


def test_read_seed_prompt_from_jsonl_by_index(tmp_path: Path) -> None:
    """The helper should read one JSONL row by index."""
    dataset = tmp_path / "dataset.jsonl"
    dataset.write_text(
        '\n'.join(
            [
                '{"query":"prompt zero"}',
                '{"query":"prompt one"}',
            ]
        )
        + '\n',
        encoding="utf-8",
    )

    prompt = _read_seed_prompt_from_jsonl(dataset, index=1)

    assert prompt == "prompt one"


def test_resolve_seed_prompt_prefers_explicit_cli_value(tmp_path: Path) -> None:
    """An explicit CLI prompt should win over any dataset path."""
    dataset = tmp_path / "dataset.jsonl"
    dataset.write_text('{"query":"dataset prompt"}\n', encoding="utf-8")
    args = argparse.Namespace(
        seed_prompt="cli prompt",
        seed_prompt_file=str(dataset),
        seed_prompt_index=0,
    )

    prompt = _resolve_seed_prompt(args)

    assert prompt == "cli prompt"
