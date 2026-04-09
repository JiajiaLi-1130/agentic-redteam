---
name: rewrite-emoji
description: Rewrite an input prompt into an emoji-heavy, indirect, metaphorical surface form.
---

# Rewrite Emoji Skill

## Purpose
Generate rewritten prompt variants using emoji-centric expression, indirect phrasing, metaphor, and surface-level lexical transformation.

## When to use
Use this skill when the agent wants a high-variance rewrite that significantly changes the visible wording and token pattern of the input.

## Inputs
- `base_prompt` (str): the source prompt to rewrite
- `num_candidates` (int, optional): number of rewrite candidates to generate
- `config` (dict, optional): optional settings for style intensity or formatting preferences

## Outputs
A JSON object with:
- `rewrites`: list of rewritten candidates
  - `text`: rewritten text
  - `strategy`: `"emoji"`
  - `metadata`: additional generation metadata

## Constraints
This skill:
- rewrites text only

## Notes
This is a transformation-only component intended to be composed with separate execution, scoring, and reflection modules.