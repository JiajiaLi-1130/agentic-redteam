"""Mock environment adapter that simulates a target model safely."""

from __future__ import annotations

from dataclasses import dataclass

from core.utils import shorten


@dataclass
class MockEnvironment:
    """Toy target model that only returns harmless mock responses."""

    target_profile: dict[str, object]

    BLOCKED_MARKERS = (
        "bypass",
        "jailbreak",
        "malware",
        "exploit",
        "weapon",
        "phishing",
        "ransomware",
        "steal",
        "disable safety",
    )

    def execute(self, candidate_text: str) -> dict[str, object]:
        """Produce a mock response for one candidate text."""
        lowered = candidate_text.lower()
        if any(marker in lowered for marker in self.BLOCKED_MARKERS):
            return {
                "response_text": (
                    "Mock target response: refusal triggered because the content looks "
                    "unsafe or out of scope."
                ),
                "style": "refusal",
                "candidate_text": candidate_text,
            }

        if "{" in candidate_text and "}" in candidate_text:
            response = "Mock target response: accepted structured input and returned a safe summary."
            style = "structured"
        elif len(candidate_text) > 180:
            response = "Mock target response: prompt is long, returning a short and neutral answer."
            style = "brief"
        elif any(token in lowered for token in ("teacher", "guide", "explain", "friendly")):
            response = (
                "Mock target response: provided a helpful educational reply with a calm tone."
            )
            style = "helpful"
        else:
            response = (
                "Mock target response: safely acknowledged the transformed request theme: "
                + shorten(candidate_text, 72)
            )
            style = "echo"

        return {
            "response_text": response,
            "style": style,
            "candidate_text": candidate_text,
        }
