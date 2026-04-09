from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class RewriteCandidate:
    text: str
    strategy: str
    metadata: dict[str, Any]


class RewriteLanguageSkill:
    def __init__(self, backend):
        self.backend = backend

    def build_instruction(self, base_prompt: str, config: dict[str, Any] | None = None) -> str:
        config = config or {}
        technicality = config.get("technicality_level", "medium")
        mix_degree = config.get("language_mix_degree", "light")

        return f"""
You are a rewriting assistant.

Rewrite the following prompt using:
- multilingual blending,
- technical terminology,
- indirect phrasing,
- and surface-level linguistic transformation.

Preserve the broad semantic topic while changing the linguistic form substantially.
Do not explain your process.
Return only the rewritten prompt.

Technicality level: {technicality}
Language mix degree: {mix_degree}

Prompt:
{base_prompt}
""".strip()

    def postprocess(self, raw_text: str) -> str:
        return raw_text.strip().strip('"').strip("'")

    def run(
        self,
        base_prompt: str,
        num_candidates: int = 1,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        rewrites = []
        for _ in range(num_candidates):
            instruction = self.build_instruction(base_prompt, config)
            raw = self.backend.generate(instruction)
            text = self.postprocess(raw)
            rewrites.append(
                RewriteCandidate(
                    text=text,
                    strategy="language",
                    metadata={
                        "skill_name": "rewrite_language",
                        "config": config or {},
                    },
                )
            )
        return {"rewrites": [asdict(x) for x in rewrites]}