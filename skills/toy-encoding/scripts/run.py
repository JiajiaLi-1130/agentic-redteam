"""Harmless encoding transformation skill."""

from __future__ import annotations

import base64
import codecs
import json
import sys


BLOCKED_MARKERS = (
    "bypass",
    "jailbreak",
    "malware",
    "exploit",
    "weapon",
    "phishing",
    "ransomware",
    "steal",
)


def sanitize_seed(text: str) -> str:
    """Replace unsafe-looking input with a harmless placeholder."""
    normalized = " ".join(text.strip().split())
    if not normalized:
        return "a neutral example topic"
    if any(marker in normalized.lower() for marker in BLOCKED_MARKERS):
        return "a harmless educational topic"
    return normalized[:140]


def load_encoding_modes(context: dict[str, object]) -> list[str]:
    """Load default or refined encoding modes from the active draft artifact."""
    draft = dict(context.get("extra", {}).get("active_skill_draft", {}))
    overrides = dict(draft.get("draft_skill", {}).get("runtime_overrides", {}))
    raw_modes = list(overrides.get("encoding_modes", []))
    modes = [str(mode).strip() for mode in raw_modes if str(mode).strip()]
    if modes:
        return modes[:4]
    return ["rot13_demo", "base64_demo", "json_wrap"]


def build_candidate(mode: str, safe_seed: str) -> dict[str, str]:
    """Build one harmless encoding candidate by mode."""
    rot13_text = codecs.encode(safe_seed, "rot_13")
    b64_text = base64.b64encode(safe_seed.encode("utf-8")).decode("ascii")
    wrapped_json = json.dumps({"request": safe_seed, "mode": "toy-demo"}, ensure_ascii=False)
    refined_json = json.dumps(
        {"request": safe_seed, "mode": "toy-refined", "tone": "gentle"},
        ensure_ascii=False,
    )
    yaml_text = f'request: "{safe_seed}"\nmode: "toy-demo"\nstyle: "friendly"'

    if mode == "rot13_demo":
        return {
            "text": f"ROT13_DEMO::{rot13_text}",
            "strategy": "rot13_demo",
            "decoded_preview": safe_seed,
        }
    if mode == "base64_demo":
        return {
            "text": f"BASE64_DEMO::{b64_text}",
            "strategy": "base64_demo",
            "decoded_preview": safe_seed,
        }
    if mode == "yaml_wrap":
        return {
            "text": f"YAML_WRAP::{yaml_text}",
            "strategy": "yaml_wrap",
            "decoded_preview": safe_seed,
        }
    if mode == "tagged_plaintext":
        return {
            "text": f"TAGGED_REQUEST::[safe-demo] {safe_seed}",
            "strategy": "tagged_plaintext",
            "decoded_preview": safe_seed,
        }
    if mode == "framed_json":
        return {
            "text": f"JSON_WRAP::{refined_json}",
            "strategy": "framed_json",
            "decoded_preview": safe_seed,
        }
    return {
        "text": f"JSON_WRAP::{wrapped_json}",
        "strategy": "json_wrap",
        "decoded_preview": safe_seed,
    }


def main() -> None:
    """Read SkillContext and emit SkillExecutionResult."""
    context = json.load(sys.stdin)
    safe_seed = sanitize_seed(str(context.get("seed_prompt", "")))

    candidates = [
        build_candidate(mode, safe_seed)
        for mode in load_encoding_modes(context)
    ]

    result = {
        "skill_name": "toy-encoding",
        "candidates": candidates,
        "rationale": "Applied harmless demonstration encodings to the sanitized seed prompt.",
        "artifacts": {
            "sanitized_seed": safe_seed,
            "encoding_count": len(candidates),
            "active_skill_version": context.get("extra", {}).get("active_skill_version"),
        },
        "metadata": {"protocol_version": "1"},
    }
    json.dump(result, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
