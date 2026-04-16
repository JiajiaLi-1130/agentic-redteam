---
name: memory-summarize
description: Use during analysis or escalation to summarize recent memory entries,
  risk-matrix context, and workflow signals for downstream selection or meta-skill
  decisions.
metadata:
  version: '1.0'
  category: analysis
  stage:
  - analysis
  - escalation
---

# memory-summarize

This harmless analysis skill summarizes recent memory entries passed in through `SkillContext.extra.recent_memory`.
It also reads the risk matrix from `SkillContext.extra.memory_matrix` and emits a structured report for downstream analysis, search selection, and meta-skill refinement.

It does not read the memory store directly.

Artifacts emitted by this skill include:

- `memory_report`: structured report with recent outcomes, risk-matrix summaries, selector context, and meta-skill context
- `memory_summary_report`: backward-compatible recent-memory summary
- `selector_context`: compact hints for search selection
- `meta_skill_context`: evidence and candidate skills for refinement/discovery
