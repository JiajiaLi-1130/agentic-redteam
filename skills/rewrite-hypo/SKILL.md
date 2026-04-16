---
name: rewrite-hypo
description: LLM-backed hypothetical framing disguise rewrite generator.
metadata:
  version: 0.1.0
---

# rewrite-hypo

This skill sends the input prompt to an OpenAI-compatible language model and asks the model to rewrite it as a hypothetical or theoretical scenario.

The current prompt instructs the model to:

- preserve the core intent of the original request
- shift the request into hypothetical framing
- make the rewritten text look more speculative or theoretical on the surface
- return structured JSON with a top-level `candidates` field

Runtime behavior:

- reads one `SkillContext` JSON object from stdin
- reads the source text from `SkillContext.seed_prompt`
- reads runtime options from `SkillContext.extra.action_args`
- reads model settings from `SkillContext.extra.skill_model_backend`
- requests exactly `candidate_count` rewritten variants
- expects each candidate to contain `text` and `strategy`
- writes one `SkillExecutionResult` JSON object to stdout
- does not apply local input filtering before sending the prompt to the model

Input/output protocol:

- input: `SkillContext JSON on stdin`
- output: `SkillExecutionResult JSON on stdout`

Artifacts emitted by this skill include:

- `original_seed`
- `candidate_count`
- `hypo_frame`
- `generation_backend`
- `generation_model`
- `active_skill_version`
