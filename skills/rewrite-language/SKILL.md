---
name: rewrite-language
description: Rewrite an input prompt using multilingual mixing, technical terminology, and indirect phrasing.
---

# Rewrite Language Skill

## Purpose
Generate rewritten prompt variants using language mixing, technical phrasing, and surface-level semantic masking.

## When to use
Use this skill when the agent wants a rewrite that changes linguistic form substantially through multilingual blending or technical re-expression.

## Inputs
- `base_prompt` (str): the source prompt to rewrite
- `num_candidates` (int, optional): number of rewrite candidates to generate
- `config` (dict, optional): optional style controls such as technicality level or language-mix intensity

## Outputs
A JSON object with:
- `rewrites`: list of rewritten candidates
  - `text`: rewritten text
  - `strategy`: `"language"`
  - `metadata`: additional generation metadata

## Constraints
This skill:
- rewrites text only