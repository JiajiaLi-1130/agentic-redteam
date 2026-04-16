---
name: refine-skill
description: Use during refinement or escalation to propose patch suggestions, runtime
  adjustments, or draft variants for an existing skill based on recent feedback.
metadata:
  version: '1.0'
  category: meta
  stage:
  - refine
  - escalation
---

# refine-skill

This meta-skill proposes a draft refinement for an existing configured skill.

It does not modify the original skill on disk.

Typical output:

- patch suggestion bullets
- a new draft skill name
- a short rationale tied to recent evaluator feedback
