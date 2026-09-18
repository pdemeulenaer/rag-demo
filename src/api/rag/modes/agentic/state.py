"""LangGraph state for bounded Agentic retrieval."""
from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from src.api.rag.contracts import EvidenceChunk
from src.api.rag.modes.agentic.contracts import AgentActionRecord


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    evidence: list[EvidenceChunk]
    actions: list[AgentActionRecord]
    fingerprints: list[str]
    rounds: int
    tool_calls: int
    planner_tokens: int
    no_progress_rounds: int
    started_at: float
    question_scope: str | None
    plan_summary: str | None
    stop_reason: str | None
    should_synthesize: bool
