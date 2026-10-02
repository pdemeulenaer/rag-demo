"""LangGraph state for bounded Agentic retrieval."""
from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from src.api.rag.contracts import EvidenceChunk
from src.api.rag.modes.agentic.contracts import AgentActionRecord, AnswerRequirement, InitialSearch


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    evidence: list[EvidenceChunk]
    requirements: list[AnswerRequirement]
    initial_searches: list[InitialSearch]
    pending_initial_searches: list[InitialSearch]
    action_need_ids: dict[str, list[str]]
    approved_build_ids: list[str]
    approved_paper_ids: list[str]
    required_build_ids: list[str]
    required_paper_titles: dict[str, str]
    required_paper_ids: list[str]
    actions: list[AgentActionRecord]
    fingerprints: list[str]
    rounds: int
    tool_calls: int
    planner_tokens: int
    next_call_estimated_tokens: int | None
    no_progress_rounds: int
    started_at: float
    question_scope: str | None
    plan_summary: str | None
    stop_reason: str | None
    should_synthesize: bool
    synthesis_policy: str
