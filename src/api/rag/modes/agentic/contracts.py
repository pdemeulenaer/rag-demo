"""Public contracts for the LangGraph Agentic RAG mode."""
from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


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
    PLANNER_FAILURE = "planner_failure"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class AgentBudget(ContractModel):
    """Hard application limits. The model cannot modify these values."""

    max_rounds: int = Field(default=3, ge=1, le=3)
    max_tool_calls: int = Field(default=12, ge=1, le=20)
    max_evidence_chunks: int = Field(default=30, ge=1, le=50)
    max_elapsed_seconds: float = Field(default=120.0, ge=5.0, le=300.0)
    max_planner_tokens: int = Field(default=6000, ge=256, le=20000)


class AgentActionRecord(ContractModel):
    """Safe tool-call detail suitable for the API, UI and traces."""

    action_id: Annotated[str, Field(min_length=1, max_length=128)]
    need_id: Annotated[str, Field(min_length=1, max_length=128)] = "graph"
    tool: Literal["search_papers", "search_chunks", "get_section", "get_neighbors"]
    status: Literal["success", "error", "skipped"]
    result_count: int = Field(ge=0)
    evidence_ids: list[str] = Field(max_length=50)
    paper_ids: list[str] = Field(max_length=20)
    error_type: Annotated[str, Field(min_length=1, max_length=100)] | None


class AgentExecutionMetadata(ContractModel):
    """Concise public execution metadata; never includes private reasoning."""

    question_scope: QuestionScope | None
    plan_summary: Annotated[str, Field(min_length=1, max_length=500)] | None
    stop_reason: StopReason
    rounds: int = Field(ge=0, le=3)
    tool_calls: int = Field(ge=0, le=20)
    evidence_count: int = Field(ge=0, le=50)
    planner_tokens: int = Field(ge=0)
    elapsed_seconds: float = Field(ge=0)
    actions: list[AgentActionRecord] = Field(max_length=20)
