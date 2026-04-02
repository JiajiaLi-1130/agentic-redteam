"""Dataclasses and JSON helpers shared by the framework."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any


def _jsonable(value: Any) -> Any:
    """Recursively convert dataclasses into JSON-serializable structures."""
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


@dataclass
class SkillSpec:
    """Machine-readable definition for a skill package."""

    name: str
    version: str
    description: str
    category: str
    stage: list[str]
    tags: list[str]
    inputs: list[str]
    outputs: list[str]
    entry: str
    references: list[str]
    failure_modes: list[str]
    root_dir: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert the spec to a plain dictionary."""
        return _jsonable(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillSpec":
        """Build a spec from a plain dictionary."""
        return cls(
            name=str(data["name"]),
            version=str(data["version"]),
            description=str(data["description"]),
            category=str(data["category"]),
            stage=list(data["stage"]),
            tags=list(data["tags"]),
            inputs=list(data["inputs"]),
            outputs=list(data["outputs"]),
            entry=str(data["entry"]),
            references=list(data["references"]),
            failure_modes=list(data["failure_modes"]),
            root_dir=str(data.get("root_dir", "")),
        )


@dataclass
class SkillContext:
    """Context passed into a skill execution."""

    run_id: str
    step_id: int
    seed_prompt: str
    target_profile: dict[str, Any]
    conversation_history: list[dict[str, Any]]
    memory_summary: dict[str, Any]
    constraints: dict[str, Any]
    prior_candidates: list[dict[str, Any]]
    evaluator_feedback: dict[str, Any]
    extra: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert the context to a plain dictionary."""
        return _jsonable(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillContext":
        """Build context from a plain dictionary."""
        return cls(
            run_id=str(data["run_id"]),
            step_id=int(data["step_id"]),
            seed_prompt=str(data["seed_prompt"]),
            target_profile=dict(data.get("target_profile", {})),
            conversation_history=list(data.get("conversation_history", [])),
            memory_summary=dict(data.get("memory_summary", {})),
            constraints=dict(data.get("constraints", {})),
            prior_candidates=list(data.get("prior_candidates", [])),
            evaluator_feedback=dict(data.get("evaluator_feedback", {})),
            extra=dict(data.get("extra", {})),
        )


@dataclass
class SkillExecutionResult:
    """Structured output returned by a skill script."""

    skill_name: str
    candidates: list[dict[str, Any]]
    rationale: str | None
    artifacts: dict[str, Any]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert the result to a plain dictionary."""
        return _jsonable(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillExecutionResult":
        """Build a skill result from a plain dictionary."""
        return cls(
            skill_name=str(data["skill_name"]),
            candidates=list(data.get("candidates", [])),
            rationale=data.get("rationale"),
            artifacts=dict(data.get("artifacts", {})),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class EvalResult:
    """Toy evaluation result for a candidate batch."""

    success: bool
    refusal_score: float
    usefulness_score: float
    diversity_score: float
    notes: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the evaluation to a plain dictionary."""
        return _jsonable(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvalResult":
        """Build an evaluation result from a plain dictionary."""
        return cls(
            success=bool(data["success"]),
            refusal_score=float(data["refusal_score"]),
            usefulness_score=float(data["usefulness_score"]),
            diversity_score=float(data["diversity_score"]),
            notes=list(data.get("notes", [])),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class MemoryEntry:
    """Persistent record of a candidate, its response, and evaluation."""

    step_id: int
    skill_name: str
    candidate_text: str
    response_text: str
    eval_result: dict[str, Any]
    tags: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert the memory entry to a plain dictionary."""
        return _jsonable(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryEntry":
        """Build a memory entry from a plain dictionary."""
        return cls(
            step_id=int(data["step_id"]),
            skill_name=str(data["skill_name"]),
            candidate_text=str(data["candidate_text"]),
            response_text=str(data["response_text"]),
            eval_result=dict(data.get("eval_result", {})),
            tags=list(data.get("tags", [])),
        )


@dataclass
class AgentState:
    """Mutable planner state tracked during the run."""

    run_id: str
    current_step: int
    seed_prompt: str
    memory_summary: dict[str, Any]
    last_eval: dict[str, Any]
    active_workflow_stage: str
    available_skills: list[str]
    budget_remaining: dict[str, Any]
    pending_candidates: list[dict[str, Any]] = field(default_factory=list)
    last_responses: list[dict[str, Any]] = field(default_factory=list)
    consecutive_failures: int = 0
    workflow_name: str = "basic"
    planner_flags: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the state to a plain dictionary."""
        return _jsonable(self)


@dataclass
class PlanStep:
    """Planner action emitted by the rule-based planner."""

    action_type: str
    target: str | None
    args: dict[str, Any]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the plan step to a plain dictionary."""
        return _jsonable(self)
