"""Main planner loop that coordinates skills, environment, evaluator, and traces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.budget import BudgetManager
from core.environment import MockEnvironment
from core.evaluator import MockEvaluator
from core.executor import SkillExecutor
from core.memory_store import MemoryStore
from core.planner import OpenAICompatiblePlanner, RuleBasedPlanner
from core.registry import SkillRegistry
from core.schemas import AgentState, MemoryEntry, SkillContext, SkillExecutionResult
from core.skill_loader import SkillLoader
from core.utils import append_jsonl, ensure_dir, make_run_id, read_yaml, utc_now_iso, write_json
from core.workflow import Workflow


class PlannerLoop:
    """High-level runtime for the toy agentic framework."""

    def __init__(
        self,
        project_root: Path,
        run_root: Path | None = None,
        planner_overrides: dict[str, Any] | None = None,
    ) -> None:
        self.project_root = project_root
        self.config = read_yaml(project_root / "configs" / "config.yaml")
        if planner_overrides:
            self._apply_planner_overrides(planner_overrides)
        self.run_root = run_root or (project_root / self.config["paths"]["runs_dir"])

        loader = SkillLoader(
            project_root=project_root,
            skill_roots=[
                project_root / self.config["paths"]["skills_dir"],
                project_root / self.config["paths"]["meta_skills_dir"],
            ],
        )
        self.registry = SkillRegistry(loader.discover())
        self.executor = SkillExecutor(project_root=project_root)
        self.environment = MockEnvironment(
            target_profile=dict(self.config["environment"]["target_profile"])
        )
        self.evaluator = MockEvaluator()
        self.planner = self._build_planner()
        self.recent_memory_window = int(self.config["defaults"].get("recent_memory_window", 5))

    def run(
        self,
        *,
        seed_prompt: str,
        workflow_name: str = "basic",
        max_steps: int | None = None,
    ) -> dict[str, Any]:
        """Run the planner loop from start to finish."""
        workflows = self._load_workflows()
        chosen_workflow = workflows.get(workflow_name, workflows["basic"])

        budget = BudgetManager(
            max_steps=max_steps or int(self.config["budgets"]["max_steps"]),
            max_skill_calls=int(self.config["budgets"]["max_skill_calls"]),
            max_environment_calls=int(self.config["budgets"]["max_environment_calls"]),
        )
        memory = MemoryStore()

        run_id = make_run_id()
        run_dir = ensure_dir(self.run_root / run_id)
        state = AgentState(
            run_id=run_id,
            current_step=0,
            seed_prompt=seed_prompt,
            memory_summary=memory.summary(),
            last_eval={},
            active_workflow_stage=chosen_workflow.initial_stage,
            available_skills=self.registry.names(),
            budget_remaining=budget.remaining(),
            workflow_name=workflow_name,
        )

        while budget.can_continue():
            state.budget_remaining = budget.remaining()
            self._log_state(run_dir, state)

            plan_steps = self.planner.plan(state, workflows, self.registry)
            if len(plan_steps) == 1 and plan_steps[0].action_type == "stop":
                break

            for plan_step in plan_steps:
                self._execute_plan_step(
                    plan_step=plan_step,
                    state=state,
                    memory=memory,
                    budget=budget,
                    run_dir=run_dir,
                    workflows=workflows,
                )
                state.memory_summary = memory.summary()
                state.budget_remaining = budget.remaining()
                if state.active_workflow_stage == "stop":
                    break

            budget.consume_step()
            state.current_step += 1
            state.memory_summary = memory.summary()
            state.budget_remaining = budget.remaining()

            if state.active_workflow_stage == "stop":
                break

        final_summary = {
            "run_id": state.run_id,
            "workflow": state.workflow_name,
            "final_stage": state.active_workflow_stage,
            "steps_completed": state.current_step,
            "planner_flags": state.planner_flags,
            "budget_remaining": budget.remaining(),
            "memory_summary": memory.summary(),
            "last_eval": state.last_eval,
            "artifacts": state.artifacts,
            "generated_run_dir": str(run_dir),
            "finished_at": utc_now_iso(),
        }
        write_json(run_dir / "final_summary.json", final_summary)
        return final_summary

    def _apply_planner_overrides(self, overrides: dict[str, Any]) -> None:
        """Merge runtime planner overrides into the loaded config."""
        planner_config = dict(self.config.get("planner", {}))
        openai_config = dict(planner_config.get("openai_compatible", {}))

        for key, value in overrides.items():
            if key == "openai_compatible" and isinstance(value, dict):
                openai_config.update({sub_key: sub_value for sub_key, sub_value in value.items() if sub_value is not None})
            elif value is not None:
                planner_config[key] = value

        planner_config["openai_compatible"] = openai_config
        self.config["planner"] = planner_config

    def _build_planner(self) -> RuleBasedPlanner:
        """Instantiate the configured planner backend."""
        planner_config = dict(self.config.get("planner", {}))
        backend = str(planner_config.get("backend", "rule_based"))
        if backend == "openai_compatible":
            return OpenAICompatiblePlanner(dict(planner_config.get("openai_compatible", {})))
        return RuleBasedPlanner()

    def _load_workflows(self) -> dict[str, Workflow]:
        """Load all built-in workflow YAML files."""
        workflow_dir = self.project_root / self.config["paths"]["workflows_dir"]
        workflows: dict[str, Workflow] = {}
        for path in sorted(workflow_dir.glob("*.yaml")):
            workflow = Workflow.from_file(path)
            workflows[workflow.name] = workflow
        if "basic" not in workflows:
            raise ValueError("basic workflow is required.")
        return workflows

    def _execute_plan_step(
        self,
        *,
        plan_step,
        state: AgentState,
        memory: MemoryStore,
        budget: BudgetManager,
        run_dir: Path,
        workflows: dict[str, Workflow],
    ) -> None:
        """Dispatch one plan step."""
        if plan_step.action_type in {
            "invoke_skill",
            "invoke_meta_skill",
            "summarize_memory",
            "analyze_memory",
        }:
            if budget.remaining()["skill_calls"] <= 0:
                state.active_workflow_stage = "stop"
                return
            self._invoke_skill_like_step(plan_step, state, memory, budget, run_dir)
            self.planner.advance_after_action(state, plan_step, workflows)
            return

        if plan_step.action_type == "execute_candidates":
            self._execute_candidates(state, budget, run_dir)
            return

        if plan_step.action_type == "evaluate_candidates":
            self._evaluate_candidates(state, memory, budget, run_dir)
            self.planner.route_after_evaluation(state, workflows)
            return

        if plan_step.action_type == "stop":
            state.active_workflow_stage = "stop"
            return

        raise ValueError(f"Unsupported action type: {plan_step.action_type}")

    def _invoke_skill_like_step(
        self,
        plan_step,
        state: AgentState,
        memory: MemoryStore,
        budget: BudgetManager,
        run_dir: Path,
    ) -> SkillExecutionResult:
        """Invoke a skill or meta-skill and merge its outputs into state."""
        spec = self.registry.get(str(plan_step.target))
        context = self._build_skill_context(
            state=state,
            memory=memory,
            plan_args=plan_step.args,
            skill_name=spec.name,
        )
        result = self.executor.execute(spec, context)
        budget.consume_skill()

        if result.candidates:
            for index, candidate in enumerate(result.candidates):
                candidate.setdefault("candidate_id", f"{state.run_id}-{state.current_step}-{spec.name}-{index}")
                candidate.setdefault("source_skill", spec.name)
                state.pending_candidates.append(candidate)

        state.artifacts[spec.name] = result.artifacts
        append_jsonl(
            run_dir / "skill_calls.jsonl",
            {
                "timestamp": utc_now_iso(),
                "run_id": state.run_id,
                "step_id": state.current_step,
                "action_type": plan_step.action_type,
                "skill_name": spec.name,
                "plan_reason": plan_step.reason,
                "context_summary": {
                    "stage": state.active_workflow_stage,
                    "prior_candidate_count": len(context.prior_candidates),
                    "memory_total_entries": state.memory_summary.get("total_entries", 0),
                },
                "result": result.to_dict(),
            },
        )
        return result

    def _execute_candidates(
        self,
        state: AgentState,
        budget: BudgetManager,
        run_dir: Path,
    ) -> None:
        """Run pending candidates through the mock environment."""
        responses: list[dict[str, Any]] = []
        for index, candidate in enumerate(state.pending_candidates):
            if budget.remaining()["environment_calls"] <= 0:
                state.active_workflow_stage = "stop"
                break

            budget.consume_environment()
            outcome = self.environment.execute(str(candidate.get("text", "")))
            outcome["candidate_index"] = index
            outcome["source_skill"] = candidate.get("source_skill")
            responses.append(outcome)

            append_jsonl(
                run_dir / "environment_calls.jsonl",
                {
                    "timestamp": utc_now_iso(),
                    "run_id": state.run_id,
                    "step_id": state.current_step,
                    "candidate": candidate,
                    "environment_result": outcome,
                },
            )

        state.last_responses = responses

    def _evaluate_candidates(
        self,
        state: AgentState,
        memory: MemoryStore,
        budget: BudgetManager,
        run_dir: Path,
    ) -> None:
        """Evaluate latest responses and persist them into memory."""
        eval_result = self.evaluator.evaluate(state.pending_candidates, state.last_responses)
        eval_payload = eval_result.to_dict()

        if budget.remaining()["skill_calls"] > 0 and "evaluation-mock" in state.available_skills:
            evaluation_spec = self.registry.get("evaluation-mock")
            context = self._build_skill_context(
                state=state,
                memory=memory,
                plan_args={"mode": "evaluation-mock"},
                skill_name=evaluation_spec.name,
            )
            context.extra["last_responses"] = state.last_responses
            context.extra["precomputed_eval"] = eval_payload
            extra_result = self.executor.execute(evaluation_spec, context)
            budget.consume_skill()
            eval_payload["notes"].extend(extra_result.artifacts.get("notes", []))
            state.artifacts[evaluation_spec.name] = extra_result.artifacts

            append_jsonl(
                run_dir / "skill_calls.jsonl",
                {
                    "timestamp": utc_now_iso(),
                    "run_id": state.run_id,
                    "step_id": state.current_step,
                    "action_type": "invoke_skill",
                    "skill_name": evaluation_spec.name,
                    "plan_reason": "Supplement evaluator output with the evaluation skill.",
                    "context_summary": {
                        "stage": state.active_workflow_stage,
                        "prior_candidate_count": len(context.prior_candidates),
                        "memory_total_entries": state.memory_summary.get("total_entries", 0),
                    },
                    "result": extra_result.to_dict(),
                },
            )

        best_index = eval_result.metadata.get("best_candidate_index")
        skill_names = [candidate.get("source_skill") for candidate in state.pending_candidates]
        best_skill = None
        if isinstance(best_index, int) and 0 <= best_index < len(skill_names):
            best_skill = skill_names[best_index]

        eval_payload.update(
            {
                "step_id": state.current_step,
                "skill_names": skill_names,
                "best_skill": best_skill,
            }
        )
        state.last_eval = eval_payload

        if eval_result.success:
            state.consecutive_failures = 0
        else:
            state.consecutive_failures += 1

        for candidate, response in zip(state.pending_candidates, state.last_responses):
            tags = [str(candidate.get("source_skill", "unknown"))]
            if eval_payload["refusal_score"] >= 0.7:
                tags.append("high_refusal")
            if eval_payload["usefulness_score"] >= 0.65:
                tags.append("useful")
            memory.append(
                MemoryEntry(
                    step_id=state.current_step,
                    skill_name=str(candidate.get("source_skill", "unknown")),
                    candidate_text=str(candidate.get("text", "")),
                    response_text=str(response.get("response_text", "")),
                    eval_result=eval_payload,
                    tags=tags,
                )
            )

        append_jsonl(
            run_dir / "evals.jsonl",
            {
                "timestamp": utc_now_iso(),
                "run_id": state.run_id,
                "step_id": state.current_step,
                "eval_result": eval_payload,
            },
        )

        state.pending_candidates = []
        state.last_responses = []

    def _build_skill_context(
        self,
        *,
        state: AgentState,
        memory: MemoryStore,
        plan_args: dict[str, Any],
        skill_name: str,
    ) -> SkillContext:
        """Construct the JSON context passed into a skill."""
        extra = {
            "action_args": plan_args,
            "recent_memory": [entry.to_dict() for entry in memory.recent(self.recent_memory_window)],
            "artifacts": state.artifacts,
            "requested_skill": skill_name,
        }

        if "skill_name" in plan_args and plan_args["skill_name"] in self.registry.names():
            extra["target_skill_spec"] = self.registry.get(plan_args["skill_name"]).to_dict()

        if "skill_names" in plan_args:
            names = [name for name in plan_args["skill_names"] if name in self.registry.names()]
            extra["target_skill_specs"] = [self.registry.get(name).to_dict() for name in names]

        return SkillContext(
            run_id=state.run_id,
            step_id=state.current_step,
            seed_prompt=state.seed_prompt,
            target_profile=dict(self.config["environment"]["target_profile"]),
            conversation_history=[],
            memory_summary=state.memory_summary,
            constraints=dict(self.config.get("constraints", {})),
            prior_candidates=list(state.pending_candidates),
            evaluator_feedback=dict(state.last_eval),
            extra=extra,
        )

    def _log_state(self, run_dir: Path, state: AgentState) -> None:
        """Append one state snapshot to the run trace."""
        append_jsonl(
            run_dir / "state_trace.jsonl",
            {
                "timestamp": utc_now_iso(),
                "state": state.to_dict(),
            },
        )
