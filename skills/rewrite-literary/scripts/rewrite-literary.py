from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class RewriteCandidate:
    text: str
    strategy: str
    metadata: dict[str, Any]


class RewriteLiterarySkill:
    def __init__(self, backend):
        self.backend = backend

    def build_instruction(self, base_prompt: str, config: dict[str, Any] | None = None) -> str:
        config = config or {}
        style = config.get("style", "poetic")

        return f"""
You are a rewriting assistant.

Rewrite the following prompt in a literary style.
Preserve the broad topic while changing the expression substantially.
Use the requested literary style consistently.
Return only the rewritten prompt.

Target style: {style}

Possible styles include:
- poetic
- narrative
- allegorical
- philosophical
- dramatic
- satirical
- mythological

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
                    strategy="literary",
                    metadata={
                        "skill_name": "rewrite_literary",
                        "config": config or {},
                    },
                )
            )
        return {"rewrites": [asdict(x) for x in rewrites]}