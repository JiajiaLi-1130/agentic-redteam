---
name: rewrite-literary
description: Rewrite an input prompt into a specified literary style such as poetic, narrative, allegorical, philosophical, or dramatic.
---

# Rewrite Literary Skill

## Purpose
Generate rewritten prompt variants using literary style transfer.

## When to use
Use this skill when the agent wants stylistic transformation rather than lexical substitution alone.

## Inputs
- `base_prompt` (str): the source prompt to rewrite
- `num_candidates` (int, optional): number of rewrite candidates to generate
- `config` (dict, optional): optional settings such as target literary style

## Outputs
A JSON object with:
- `rewrites`: list of rewritten candidates
  - `text`: rewritten text
  - `strategy`: `"literary"`
  - `metadata`: additional generation metadata

## Constraints
This skill:
- rewrites text only