---
name: retrieval-analysis
description: Analyze recent failures and memory patterns.
metadata:
  version: "1.0"
---

# retrieval-analysis

This analysis skill looks at recent memory and evaluator feedback and extracts patterns such as:

- repeated refusal tags
- which skills were recently used
- whether usefulness looks flat or improving

It consumes `SkillContext.extra.artifacts["memory-summarize"].memory_report` when available, plus `SkillContext.extra.memory_matrix`.
Its output is designed for both runtime selection and meta-skills that update existing skills or draft new ones.

Artifacts emitted by this skill include:

- `analysis_report`: structured analysis over recent memory, memory report, and risk matrix
- `selector_context`: recommended, avoided, and underexplored skills for future selection
- `meta_skill_context`: failure patterns, candidate refinement targets, skill combinations, and refinement guidance
