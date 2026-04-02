# Skill-Based Automated Safety Evaluation / Red-Team Research Framework

This project is a minimal, runnable Python framework for studying an agentic workflow built around a stable runtime kernel and a pluggable skill space.

All bundled skills are harmless toy examples. They only perform mock prompt transformations, memory analysis, and mock evaluation so the architecture can be studied without implementing real-world jailbreaks, evasions, or unsafe behaviors.

## Project Goal

The framework demonstrates:

- a fixed kernel for planning, execution, memory, evaluation, budgeting, and tracing
- a normal skill space for transform and analysis skills
- a meta-skill space for refinement, combination, and discovery of new toy skills
- a rule-based planner that decides when to call skills, memory analysis, environment execution, and meta-skills

## Architecture

```text
                     +--------------------+
                     |      main.py       |
                     +----------+---------+
                                |
                                v
                     +--------------------+
                     |   Planner Loop     |
                     | state + workflow   |
                     +----+----+----+-----+
                          |    |    |
            +-------------+    |    +------------------+
            |                  |                       |
            v                  v                       v
   +----------------+  +---------------+     +-------------------+
   | Skill Registry |  | Memory Store  |     |  Budget Manager   |
   | + Loader       |  | + Summaries   |     | step/skill/env    |
   +--------+-------+  +-------+-------+     +---------+---------+
            |                      |                       |
            v                      |                       |
   +--------------------+          |                       |
   | Skill Executor     |          |                       |
   | stdin/stdout JSON  |          |                       |
   +----------+---------+          |                       |
              |                    |                       |
      +-------+-------+            |                       |
      |               |            |                       |
      v               v            v                       v
+-------------+ +---------------+ +----------------+ +----------------+
| skills/     | | meta_skills/  | | Mock Env       | | Mock Evaluator |
| toy skills  | | skill drafts  | | target model   | | toy metrics     |
+-------------+ +---------------+ +----------------+ +----------------+
```

## Directory Layout

```text
project_root/
├── README.md
├── requirements.txt
├── main.py
├── configs/
├── core/
├── skills/
├── meta_skills/
├── runs/
└── tests/
```

## Install

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python main.py --seed_prompt "Explain how rainbows form in simple language." --workflow basic --max_steps 5
```

## Minimal Example

```bash
python main.py \
  --seed_prompt "Describe the lifecycle of a butterfly with a friendly tone." \
  --workflow basic \
  --max_steps 4
```

The run writes artifacts to `runs/<run_id>/`:

- `state_trace.jsonl`
- `skill_calls.jsonl`
- `environment_calls.jsonl`
- `evals.jsonl`
- `final_summary.json`

## Remote Planner Backend

The default planner remains rule-based and fully offline. The repository also supports an optional OpenAI-compatible planning backend for a vLLM-served model.

The bundled config already includes an example planner endpoint:

- base URL: `http://s-20260330192936-zlwm5-decode.ailab-safethm.svc:23297/v1`
- model: `orm`
- API key: `FAKE_API_KEY`

To enable it, either set `planner.backend: openai_compatible` in `configs/config.yaml` or pass CLI overrides:

```bash
python main.py \
  --seed_prompt "Explain cloud formation safely." \
  --workflow basic \
  --planner_backend openai_compatible \
  --planner_base_url "http://s-20260330192936-zlwm5-decode.ailab-safethm.svc:23297/v1" \
  --planner_model orm \
  --planner_api_key FAKE_API_KEY
```

The remote planner only chooses structured next actions. It never generates candidate text, and the runtime validates its JSON output before executing anything. If the remote call fails or returns invalid JSON, the system falls back to the rule-based planner.

## Skill Protocol

Each skill directory contains:

- `SKILL.md`: human-readable documentation
- `skill.json`: machine-readable spec
- `scripts/run.py`: executable entrypoint

All `scripts/run.py` files must:

1. read a JSON `SkillContext` object from stdin
2. write a JSON `SkillExecutionResult` object to stdout
3. avoid direct access to memory store or environment
4. remain stateless and as function-like as possible

## Adding A Skill

1. Create a new directory under `skills/`.
2. Add `SKILL.md`, `skill.json`, and `scripts/run.py`.
3. Make `skill.json` conform to `core.schemas.SkillSpec`.
4. Make `scripts/run.py` read stdin JSON and emit stdout JSON.
5. Place any human-readable guidance in `references/`.

## Adding A Meta-Skill

1. Create a new directory under `meta_skills/`.
2. Mark its `category` as `meta` in `skill.json`.
3. Keep it harmless and focused on toy skill drafts or patch suggestions.
4. Do not let it overwrite existing skills directly.

## Current Limitations

- The planner is rule-based and not LLM-driven.
- The environment is a mock target model.
- The evaluator is a toy heuristic.
- Meta-skills only generate draft suggestions and never mutate code automatically.
- No real attack, jailbreak, bypass, deception, or evasion behavior is implemented.

## Extension Ideas

- add richer workflow condition language
- add persistent vector or graph memory backends
- add offline experiment replay and comparison tooling
- add skill versioning and draft-to-approved promotion flows
- add richer candidate ranking and diversity management
- add pluggable local models for planning while preserving safety constraints
