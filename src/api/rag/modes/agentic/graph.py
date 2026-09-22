"""LangGraph orchestration for bounded, tool-calling Agentic retrieval."""
from __future__ import annotations

import logging
from time import monotonic

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from src.api.rag.contracts import EvidenceChunk
from src.api.rag.modes.agentic.contracts import (
    AgentActionRecord,
    AgentBudget,
    StopReason,
)
from src.api.rag.modes.agentic.policies import action_fingerprint
from src.api.rag.modes.agentic.state import AgentState
from src.api.rag.modes.agentic.tools import TERMINAL_TOOLS


logger = logging.getLogger(__name__)
RETRIEVAL_TOOL_NAMES = {"search_papers", "search_chunks", "get_section", "get_neighbors"}
TERMINAL_TOOL_NAMES = {"finish_with_evidence", "abstain"}
QUESTION_SCOPES = {"direct", "within_paper", "cross_paper", "metadata_discovery"}

SYSTEM_PROMPT = """You are a retrieval agent for a scientific-paper RAG system.
Use the supplied read-only tools to gather answer evidence from the approved corpus.

Rules:
- For a broad factual question, start with one focused hybrid search_chunks call.
- Use sparse search for exact identifiers, acronyms, catalogue numbers and named objects;
  use dense search for conceptual paraphrases; use hybrid when both signals are useful.
- Use search_papers only to resolve a named paper or metadata constraint.
- Call get_section/get_neighbors only with exact identifiers seen in tool results.
- Never invent identifiers, repeat an identical call, or request mutation/code execution.
- Tool metadata alone is not answer evidence; answers require retrieved chunks.
- When chunks provide potentially useful answer evidence, call finish_with_evidence with a
  concise public summary. The shared grounded generator, not this planner, makes the final
  answer from those chunks and may still state that a detail is unsupported.
- Call abstain only after retrieval returned no potentially relevant chunks and no useful
  reformulation remains. Never return a plain-text answer.
- Do not mix a terminal tool with retrieval tools in the same response.
"""

EVIDENCE_FALLBACK_REASONS = {
    StopReason.MAX_ROUNDS,
    StopReason.TOOL_CALL_BUDGET,
    StopReason.EVIDENCE_BUDGET,
    StopReason.TIME_BUDGET,
    StopReason.TOKEN_BUDGET,
    StopReason.REPEATED_ACTION,
    StopReason.NO_PROGRESS,
    StopReason.TOOL_FAILURE,
    StopReason.PLANNER_FAILURE,
    StopReason.INSUFFICIENT_EVIDENCE,
}


def _terminate(state: AgentState, reason: StopReason, *, summary: str | None = None) -> dict:
    """Stop retrieval, but preserve already collected evidence for grounded synthesis."""
    use_evidence = bool(state.get("evidence")) and reason in EVIDENCE_FALLBACK_REASONS
    update = {
        "stop_reason": reason.value,
        "should_synthesize": use_evidence,
        "synthesis_policy": "evidence_fallback" if use_evidence else "hard_stop",
    }
    if summary is not None:
        update["plan_summary"] = summary
    return update


def _token_usage(message: AIMessage) -> int:
    usage = getattr(message, "usage_metadata", None) or {}
    if isinstance(usage, dict):
        return int(usage.get("total_tokens") or 0)
    return int(getattr(usage, "total_tokens", 0) or 0)


def _route_guard(state: AgentState) -> str:
    return END if state.get("stop_reason") else "tools"


def _route_collect(state: AgentState) -> str:
    return END if state.get("stop_reason") else "agent"


def build_agent_graph(*, model, retrieval_tools: list, budget: AgentBudget):
    """Compile one request-scoped graph with native LangChain tool schemas."""
    bound_model = model.bind_tools([*retrieval_tools, *TERMINAL_TOOLS])

    def call_agent(state: AgentState) -> dict:
        try:
            response = bound_model.invoke(state["messages"])
        except Exception as exc:
            logger.exception("Agentic model call failed (%s)", type(exc).__name__)
            return _terminate(
                state, StopReason.PLANNER_FAILURE,
                summary="The LangGraph agent model call failed after bounded retrieval.",
            )
        if not isinstance(response, AIMessage):
            logger.error("Agentic model returned %s instead of AIMessage", type(response).__name__)
            return _terminate(
                state, StopReason.PLANNER_FAILURE,
                summary="The LangGraph agent returned an invalid response.",
            )
        return {
            "messages": [response],
            "planner_tokens": state.get("planner_tokens", 0) + _token_usage(response),
        }

    def guard(state: AgentState) -> dict:
        if state.get("stop_reason"):
            return {}
        message = state["messages"][-1]
        calls = message.tool_calls if isinstance(message, AIMessage) else []
        if not calls:
            return _terminate(
                state, StopReason.PLANNER_FAILURE,
                summary="The agent did not select a valid retrieval or terminal tool.",
            )

        terminal = [call for call in calls if call["name"] in TERMINAL_TOOL_NAMES]
        retrieval = [call for call in calls if call["name"] in RETRIEVAL_TOOL_NAMES]
        unknown = [call for call in calls
                   if call["name"] not in TERMINAL_TOOL_NAMES | RETRIEVAL_TOOL_NAMES]
        if unknown or (terminal and (retrieval or len(terminal) != 1)):
            return _terminate(
                state, StopReason.PLANNER_FAILURE,
                summary="The agent selected an invalid combination of tools.",
            )
        if terminal:
            call = terminal[0]
            args = call.get("args") or {}
            summary = str(args.get("summary") or "Agentic retrieval completed.")[:500]
            scope = args.get("question_scope")
            if scope not in QUESTION_SCOPES:
                return _terminate(
                    state, StopReason.PLANNER_FAILURE,
                    summary="The agent returned an invalid question scope.",
                )
            can_finish = call["name"] == "finish_with_evidence" and bool(state.get("evidence"))
            if can_finish:
                return {
                    "stop_reason": StopReason.SUFFICIENT.value,
                    "should_synthesize": True,
                    "synthesis_policy": "model_finish",
                    "question_scope": scope,
                    "plan_summary": summary,
                }
            update = _terminate(
                state, StopReason.INSUFFICIENT_EVIDENCE, summary=summary,
            )
            update["question_scope"] = scope
            return update

        elapsed = monotonic() - state["started_at"]
        if elapsed >= budget.max_elapsed_seconds:
            return _terminate(state, StopReason.TIME_BUDGET)
        if state.get("planner_tokens", 0) >= budget.max_planner_tokens:
            return _terminate(state, StopReason.TOKEN_BUDGET)
        if state.get("rounds", 0) >= budget.max_rounds:
            return _terminate(state, StopReason.MAX_ROUNDS)
        if state.get("tool_calls", 0) + len(retrieval) > budget.max_tool_calls:
            return _terminate(state, StopReason.TOOL_CALL_BUDGET)
        if len(state.get("evidence", [])) >= budget.max_evidence_chunks:
            return _terminate(state, StopReason.EVIDENCE_BUDGET)

        known = set(state.get("fingerprints", []))
        requested = [action_fingerprint(call["name"], call.get("args") or {})
                     for call in retrieval]
        if len(requested) != len(set(requested)) or known.intersection(requested):
            return _terminate(
                state, StopReason.REPEATED_ACTION,
                summary="The agent repeated an identical retrieval action.",
            )
        return {
            "fingerprints": [*state.get("fingerprints", []), *requested],
            "plan_summary": state.get("plan_summary") or (
                "The LangGraph agent is gathering supporting paper evidence."
            ),
        }

    def collect(state: AgentState) -> dict:
        last_ai_index = max(
            index for index, message in enumerate(state["messages"])
            if isinstance(message, AIMessage)
        )
        ai_message = state["messages"][last_ai_index]
        tool_messages = [message for message in state["messages"][last_ai_index + 1:]
                         if isinstance(message, ToolMessage)]
        calls = {call["id"]: call for call in ai_message.tool_calls}
        evidence_by_id = {row.id: row for row in state.get("evidence", [])}
        records = list(state.get("actions", []))
        new_information = 0
        errors = 0

        for message in tool_messages:
            call = calls.get(message.tool_call_id, {})
            name = call.get("name", message.name)
            artifact = message.artifact if isinstance(message.artifact, dict) else {}
            is_error = getattr(message, "status", "success") == "error" or not artifact
            accepted: list[EvidenceChunk] = []
            paper_ids: list[str] = []
            result_count = 0
            if is_error:
                errors += 1
            else:
                chunks = [EvidenceChunk.model_validate(row)
                          for row in artifact.get("chunks", [])]
                papers = artifact.get("papers", [])
                result_count = len(chunks) + len(papers)
                new_information += len(papers)
                paper_ids.extend(str(row["paper_id"]) for row in papers)
                remaining = budget.max_evidence_chunks - len(evidence_by_id)
                for chunk in chunks:
                    if chunk.id in evidence_by_id or remaining <= 0:
                        continue
                    evidence_by_id[chunk.id] = chunk
                    accepted.append(chunk)
                    paper_ids.append(chunk.paper_id)
                    new_information += 1
                    remaining -= 1
            records.append(AgentActionRecord(
                action_id=str(message.tool_call_id), tool=name,
                status="error" if is_error else "success",
                result_count=result_count,
                evidence_ids=[row.id for row in accepted],
                paper_ids=list(dict.fromkeys(paper_ids))[:20],
                error_type="ToolExecutionError" if is_error else None,
            ))

        next_no_progress = (
            state.get("no_progress_rounds", 0) + 1 if new_information == 0 else 0
        )
        update = {
            "evidence": list(evidence_by_id.values()),
            "actions": records,
            "rounds": state.get("rounds", 0) + 1,
            "tool_calls": state.get("tool_calls", 0) + len(tool_messages),
            "no_progress_rounds": next_no_progress,
        }
        if tool_messages and errors == len(tool_messages):
            update.update(_terminate(update, StopReason.TOOL_FAILURE))
        elif next_no_progress >= 2:
            update.update(_terminate(update, StopReason.NO_PROGRESS))
        elif monotonic() - state["started_at"] >= budget.max_elapsed_seconds:
            update.update(_terminate(update, StopReason.TIME_BUDGET))
        return update

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_agent)
    graph.add_node("guard", guard)
    graph.add_node("tools", ToolNode(
        retrieval_tools, handle_tool_errors=lambda exc: f"{type(exc).__name__}: {exc}"
    ))
    graph.add_node("collect", collect)
    graph.add_edge(START, "agent")
    graph.add_edge("agent", "guard")
    graph.add_conditional_edges("guard", _route_guard, {"tools": "tools", END: END})
    graph.add_edge("tools", "collect")
    graph.add_conditional_edges("collect", _route_collect, {"agent": "agent", END: END})
    return graph.compile()
