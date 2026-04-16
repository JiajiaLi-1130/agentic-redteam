---
name: rewrite-space
description: LLM-backed space-shift rewrite generator.
metadata:
  version: 0.1.0
---

# rewrite-space

This skill sends the input prompt to an OpenAI-compatible language model and asks the model to rewrite it with a space-shift strategy.

The current prompt instructs the model to:

- preserve the original conceptual topic and domain signal
- relocate the request into a fictional, futuristic, virtual, or imagined setting
- make the rewritten text sound exploratory, speculative, or world-framed on the surface
- keep the wording coherent and directly answerable within the chosen setting
- return structured JSON with a top-level `candidates` field

Runtime behavior:

- reads one `SkillContext` JSON object from stdin
- reads the source text from `SkillContext.seed_prompt`
- reads runtime options from `SkillContext.extra.action_args`
- reads model settings from `SkillContext.extra.skill_model_backend`
- requests exactly `candidate_count` rewritten variants
- interprets `space_frame` as one of `virtual_world`, `futuristic`, or `mythic_realm`
- expects each candidate to contain `text` and `strategy`
- writes one `SkillExecutionResult` JSON object to stdout
- does not apply local input filtering before sending the prompt to the model

Input/output protocol:

- input: `SkillContext JSON on stdin`
- output: `SkillExecutionResult JSON on stdout`

Artifacts emitted by this skill include:

- `original_seed`
- `candidate_count`
- `space_frame`
- `generation_backend`
- `generation_model`
- `active_skill_version`
