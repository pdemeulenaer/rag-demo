"""Public contracts for the LangGraph Agentic RAG mode."""
from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AnswerRequirement(ContractModel):
    """An answer task, fixed before retrieval and independent of tool calls."""

    id: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=2000)
    kind: Literal["fact", "synthesis"] = "fact"
    effect_parameters: list[str] = Field(default_factory=list, max_length=20)


class ParameterEffectNeed(ContractModel):
    """Separate a requested parameter response from its optional baseline measurement."""

    requirement_index: int = Field(strict=True, ge=1, le=20)
    baseline_requirement_index: int | None = Field(default=None, strict=True, ge=1, le=20,
        description="Different factual description index when the question ALSO requests the baseline; null only for an effect-only request.")
    parameter: str = Field(min_length=1, max_length=150, description=(
        "Short literal name from the ORIGINAL question, including distinguishing qualifiers. "
        "Do not replace a requested outer/physical/projected parameter with another parameter."))


class ParameterEffectEvidence(ContractModel):
    """Planner's observable support decision, not private reasoning or semantic proof."""

    need_id: str = Field(min_length=1, max_length=128)
    context_id: str = Field(min_length=1, max_length=128)
    parameter_quote: str = Field(min_length=1, max_length=500)
    outcome_quote: str = Field(min_length=1, max_length=1000)
    outcome_kind: Literal["reported_change", "reported_no_change", "baseline", "settings_only", "other_parameter"]


class InitialSearch(ContractModel):
    """Native tool input: a search strategy, distinct from answer requirements."""

    query: str = Field(min_length=1, max_length=500)
    requirement_indices: list[Annotated[int, Field(strict=True, ge=1, le=20)]] = Field(
        min_length=1, max_length=20)
    retrieval_mode: Literal["dense", "sparse", "hybrid"] = "hybrid"
    build_ids: list[str] = Field(default_factory=list, max_length=20)
    paper_ids: list[str] = Field(default_factory=list, max_length=20)
    limit: int = Field(default=8, strict=True, ge=1, le=20)


class QuestionScope(StrEnum):
    DIRECT = "direct"
    WITHIN_PAPER = "within_paper"
    CROSS_PAPER = "cross_paper"
    METADATA_DISCOVERY = "metadata_discovery"


class StopReason(StrEnum):
    SUFFICIENT = "sufficient"
    MAX_ROUNDS = "max_rounds"
    TOOL_CALL_BUDGET = "tool_call_budget"
    EVIDENCE_BUDGET = "evidence_budget"
    TIME_BUDGET = "time_budget"
    TOKEN_BUDGET = "token_budget"
    REPEATED_ACTION = "repeated_action"
    NO_PROGRESS = "no_progress"
    TOOL_FAILURE = "tool_failure"
    PLANNER_FAILURE = "planner_failure"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class AgentBudget(ContractModel):
    """Hard application limits. The model cannot modify these values."""

    max_rounds: int = Field(default=3, ge=1, le=5)
    max_tool_calls: int = Field(default=12, ge=1, le=20)
    max_parallel_tools: int = Field(default=4, ge=1, le=8)
    max_evidence_chunks: int = Field(default=30, ge=1, le=50)
    max_elapsed_seconds: float = Field(default=120.0, ge=5.0, le=300.0)
    max_planner_tokens: int = Field(default=20000, ge=256, le=40000)


class AgentActionRecord(ContractModel):
    """Safe tool-call detail suitable for the API, UI and traces."""

    action_id: Annotated[str, Field(min_length=1, max_length=128)]
    need_id: Annotated[str, Field(min_length=1, max_length=128)]
    need_ids: list[str] = Field(default_factory=list, max_length=20)
    tool: Literal["search_papers", "search_chunks", "get_section", "get_neighbors"]
    query: Annotated[str, Field(min_length=1, max_length=500)] | None = None
    status: Literal["success", "error", "skipped"]
    result_count: int = Field(ge=0)
    evidence_ids: list[str] = Field(max_length=50)
    paper_ids: list[str] = Field(max_length=20)
    error_type: Annotated[str, Field(min_length=1, max_length=100)] | None


class RequirementValidationIssue(ContractModel):
    """Safe field paths, codes and static guidance; never rejected values/reasoning."""

    field: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=100)
    message: str | None = Field(default=None, min_length=1, max_length=500)


class RequirementValidationFailure(ContractModel):
    attempt: int = Field(ge=1, le=2)
    issues: list[RequirementValidationIssue] = Field(max_length=20)


class AgentExecutionMetadata(ContractModel):
    """Concise public execution metadata; never includes private reasoning."""

    question_scope: QuestionScope | None
    plan_summary: Annotated[str, Field(min_length=1, max_length=500)] | None
    stop_reason: StopReason
    synthesis_policy: Literal["model_finish", "evidence_fallback", "hard_stop"] = "hard_stop"
    rounds: int = Field(ge=0, le=5)
    tool_calls: int = Field(ge=0, le=20)
    evidence_count: int = Field(ge=0, le=50)
    required_paper_count: int = Field(default=0, ge=0, le=20)
    covered_required_paper_count: int = Field(default=0, ge=0, le=20)
    missing_required_build_ids: list[str] = Field(default_factory=list, max_length=20)
    required_evidence_need_count: int = Field(default=0, ge=0, le=20)
    covered_evidence_need_count: int = Field(default=0, ge=0, le=20)
    missing_evidence_need_ids: list[str] = Field(default_factory=list, max_length=20)
    planner_tokens: int = Field(ge=0)
    next_call_estimated_tokens: int | None = Field(default=None, ge=0)
    planner_context_compactions: int = Field(default=0, ge=0)
    planner_context_compaction_attempts: int = Field(default=0, ge=0)
    requirement_correction_attempts: int = Field(default=0, ge=0, le=1)
    requirement_validation_failures: list[RequirementValidationFailure] = Field(
        default_factory=list, max_length=2)
    elapsed_seconds: float = Field(ge=0)
    actions: list[AgentActionRecord] = Field(max_length=20)
    requirements: list[AnswerRequirement] = Field(default_factory=list, max_length=20)
    parameter_effects: list[ParameterEffectNeed] = Field(default_factory=list, max_length=20)
    effect_finish_checks: list[dict] = Field(default_factory=list, max_length=11)
    initial_searches: list[InitialSearch] = Field(default_factory=list, max_length=20)
    max_parallel_tools: int = Field(default=4, ge=1, le=8)
