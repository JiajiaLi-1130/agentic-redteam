---
name: toy-persona
version: 0.1.0
description: Harmless persona-style prompt rewriting for toy candidate generation.
---

# toy-persona

This harmless toy skill rewrites the seed prompt into a few role-framed variants.

It is only a structural example for the framework:

- no real bypass behavior
- no unsafe instructions
- blocked terms are replaced with a neutral placeholder topic

## Input

- `SkillContext.seed_prompt`

## Output

- `SkillExecutionResult.candidates`

## Notes

The generated personas are intentionally benign, such as teacher, curator, or librarian voices.
