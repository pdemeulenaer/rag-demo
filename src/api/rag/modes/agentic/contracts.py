"""Strict plans, actions, sufficiency decisions and budgets for Agentic RAG.

These schemas intentionally contain concise, auditable summaries rather than
private chain-of-thought. They describe what evidence is needed and which
read-only operation may run; they never contain executable code or mutations.
"""
from __future__ import annotations

import json
from enum import StrEnum
from hashlib import sha256
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


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
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


Identifier = Annotated[str, Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")]
ShortText = Annotated[str, Field(min_length=1, max_length=500)]


class EvidenceNeed(ContractModel):
    """One independently checkable information requirement."""

    need_id: Identifier
    subquestion: ShortText
    success_criteria: ShortText
    target_paper_ids: list[str] = Field(max_length=20)

    @model_validator(mode="after")
    def validate_targets(self) -> "EvidenceNeed":
        if len(self.target_paper_ids) != len(set(self.target_paper_ids)):
            raise ValueError("Target paper IDs must be unique")
        return self


class ToolActionBase(ContractModel):
    action_id: Identifier
    need_id: Identifier


class SearchPapersAction(ToolActionBase):
    tool: Literal["search_papers"]
    title: Annotated[str, Field(min_length=1, max_length=300)] | None
    author: Annotated[str, Field(min_length=1, max_length=200)] | None
    year: Annotated[int, Field(ge=1900, le=2100)] | None
    terms: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(max_length=10)
    source: Literal["arxiv", "uploads"] | None
    limit: int = Field(ge=1, le=10)


class SearchChunksAction(ToolActionBase):
    tool: Literal["search_chunks"]
    query: Annotated[str, Field(min_length=1, max_length=500)]
    retrieval_mode: Literal["vanilla", "hybrid"]
    build_ids: list[str] = Field(max_length=20)
    paper_ids: list[str] = Field(max_length=20)
    limit: int = Field(ge=1, le=20)

    @model_validator(mode="after")
    def validate_filters(self) -> "SearchChunksAction":
        if len(self.build_ids) != len(set(self.build_ids)):
            raise ValueError("Chunk-search build IDs must be unique")
        if len(self.paper_ids) != len(set(self.paper_ids)):
            raise ValueError("Chunk-search paper IDs must be unique")
        return self


class GetSectionAction(ToolActionBase):
    tool: Literal["get_section"]
    build_id: Annotated[str, Field(min_length=1, max_length=100)]
    paper_id: Annotated[str, Field(min_length=1, max_length=100)]
    section_header: Annotated[str, Field(min_length=1, max_length=500)]
    limit: int = Field(ge=1, le=50)


class GetNeighborsAction(ToolActionBase):
    tool: Literal["get_neighbors"]
    build_id: Annotated[str, Field(min_length=1, max_length=100)]
    paper_id: Annotated[str, Field(min_length=1, max_length=100)]
    chunk_index: int = Field(ge=0)
    before: int = Field(ge=0, le=5)
    after: int = Field(ge=0, le=5)


ToolAction = Annotated[
    SearchPapersAction | SearchChunksAction | GetSectionAction | GetNeighborsAction,
    Field(discriminator="tool"),
]


class AgentPlan(ContractModel):
    """Initial evidence plan emitted by the planner."""

    schema_version: Literal[1]
    question_scope: QuestionScope
    plan_summary: Annotated[str, Field(min_length=1, max_length=500)]
    evidence_needs: list[EvidenceNeed] = Field(min_length=1, max_length=6)
    initial_actions: list[ToolAction] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def validate_references(self) -> "AgentPlan":
        need_ids = [need.need_id for need in self.evidence_needs]
        action_ids = [action.action_id for action in self.initial_actions]
        if len(need_ids) != len(set(need_ids)):
            raise ValueError("Evidence need IDs must be unique")
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("Initial action IDs must be unique")
        unknown = {action.need_id for action in self.initial_actions}.difference(need_ids)
        if unknown:
            raise ValueError("Every initial action must reference a declared evidence need")
        return self


class NeedAssessment(ContractModel):
    """Auditable evidence coverage for one need, without hidden reasoning."""

    need_id: Identifier
    satisfied: bool
    evidence_ids: list[str] = Field(max_length=50)
    missing_evidence: Annotated[str, Field(min_length=1, max_length=300)] | None

    @model_validator(mode="after")
    def validate_coverage(self) -> "NeedAssessment":
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("Assessment evidence IDs must be unique")
        if self.satisfied and self.missing_evidence is not None:
            raise ValueError("A satisfied need cannot report missing evidence")
        if self.satisfied and not self.evidence_ids:
            raise ValueError("A satisfied need must cite evidence")
        if not self.satisfied and self.missing_evidence is None:
            raise ValueError("An unsatisfied need must describe missing evidence")
        return self


class SufficiencyDecision(ContractModel):
    """One bounded decision after inspecting accumulated evidence."""

    schema_version: Literal[1]
    decision: Literal["synthesize", "continue", "abstain"]
    summary: Annotated[str, Field(min_length=1, max_length=500)]
    assessments: list[NeedAssessment] = Field(min_length=1, max_length=6)
    next_actions: list[ToolAction] = Field(max_length=6)
    stop_reason: StopReason | None

    @model_validator(mode="after")
    def validate_decision(self) -> "SufficiencyDecision":
        need_ids = [assessment.need_id for assessment in self.assessments]
        action_ids = [action.action_id for action in self.next_actions]
        if len(need_ids) != len(set(need_ids)):
            raise ValueError("Assessment need IDs must be unique")
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("Next action IDs must be unique")
        if self.decision == "continue":
            if not self.next_actions or self.stop_reason is not None:
                raise ValueError("Continue requires actions and no stop reason")
            if all(assessment.satisfied for assessment in self.assessments):
                raise ValueError("Continue requires at least one unsatisfied need")
        else:
            if self.next_actions or self.stop_reason is None:
                raise ValueError("A terminal decision requires a stop reason and no actions")
        if self.decision == "synthesize":
            if self.stop_reason != StopReason.SUFFICIENT or not all(
                assessment.satisfied for assessment in self.assessments
            ):
                raise ValueError("Synthesis requires all needs satisfied")
        if self.decision == "abstain" and self.stop_reason == StopReason.SUFFICIENT:
            raise ValueError("Abstention cannot use the sufficient stop reason")
        if self.decision == "abstain" and all(
            assessment.satisfied for assessment in self.assessments
        ):
            raise ValueError("Abstention requires at least one unsatisfied need")
        return self


class AgentBudget(ContractModel):
    """Hard executor limits selected by application configuration, not the planner."""

    max_rounds: int = Field(default=3, ge=1, le=3)
    max_tool_calls: int = Field(default=12, ge=1, le=20)
    max_evidence_chunks: int = Field(default=30, ge=1, le=50)
    max_elapsed_seconds: float = Field(default=120.0, ge=5.0, le=300.0)
    max_planner_tokens: int = Field(default=6000, ge=256, le=20000)


class BudgetUsage(ContractModel):
    rounds: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    evidence_chunks: int = Field(default=0, ge=0)
    elapsed_seconds: float = Field(default=0.0, ge=0.0)
    planner_tokens: int = Field(default=0, ge=0)


def action_fingerprint(action: ToolAction) -> str:
    """Identify a repeated tool operation independently of planner-local IDs."""
    payload = action.model_dump(mode="json", exclude={"action_id", "need_id"})
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode()).hexdigest()


def budget_stop_reason(budget: AgentBudget, usage: BudgetUsage) -> StopReason | None:
    """Return the first exhausted hard budget using deterministic precedence."""
    if usage.rounds >= budget.max_rounds:
        return StopReason.MAX_ROUNDS
    if usage.tool_calls >= budget.max_tool_calls:
        return StopReason.TOOL_CALL_BUDGET
    if usage.evidence_chunks >= budget.max_evidence_chunks:
        return StopReason.EVIDENCE_BUDGET
    if usage.elapsed_seconds >= budget.max_elapsed_seconds:
        return StopReason.TIME_BUDGET
    if usage.planner_tokens >= budget.max_planner_tokens:
        return StopReason.TOKEN_BUDGET
    return None


def validate_decision_for_plan(plan: AgentPlan, decision: SufficiencyDecision) -> None:
    """Validate round output against the immutable initial evidence needs."""
    expected = {need.need_id for need in plan.evidence_needs}
    assessed = {assessment.need_id for assessment in decision.assessments}
    if assessed != expected:
        raise ValueError("A sufficiency decision must assess every planned evidence need")
    if any(action.need_id not in expected for action in decision.next_actions):
        raise ValueError("Every next action must reference a planned evidence need")
