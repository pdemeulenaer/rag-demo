"""Public adapter from the RAG pipeline to the LangGraph retrieval graph."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from time import monotonic

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.api.core.config import config
from src.api.observability.tracing import (
    langchain_callback,
    observe,
    update_span,
)
from src.api.rag.contracts import EvidenceChunk, RetrievalScope
from src.api.rag.modes.agentic.contracts import (
    AgentBudget,
    AgentExecutionMetadata,
    StopReason,
)
from src.api.rag.modes.agentic.graph import SYSTEM_PROMPT, build_agent_graph
from src.api.rag.modes.agentic.tools import build_retrieval_tools


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentRunResult:
    evidence: list[EvidenceChunk]
    execution: AgentExecutionMetadata
    should_synthesize: bool


def _default_model():
    kwargs = {
        "model": config.AGENT_MODEL,
        "api_key": config.OPENAI_API_KEY,
        "max_completion_tokens": config.AGENT_MAX_COMPLETION_TOKENS,
    }
    if config.AGENT_REASONING_EFFORT and config.AGENT_REASONING_EFFORT != "none":
        kwargs["reasoning_effort"] = config.AGENT_REASONING_EFFORT
    return ChatOpenAI(**kwargs)


def _failed(started: float, reason: StopReason) -> AgentRunResult:
    return AgentRunResult(
        evidence=[],
        execution=AgentExecutionMetadata(
            question_scope=None,
            plan_summary="The LangGraph retrieval agent failed safely.",
            stop_reason=reason,
            rounds=0,
            tool_calls=0,
            evidence_count=0,
            planner_tokens=0,
            elapsed_seconds=round(max(0.0, monotonic() - started), 3),
            actions=[],
        ),
        should_synthesize=False,
    )


@observe(name="agentic_retrieval", capture_input=False, capture_output=False)
def run_agentic(question: str, *, client, catalogue, scope: RetrievalScope,
                 embed: Callable[[str], list[float]], budget: AgentBudget | None = None,
                 model=None) -> AgentRunResult:
    """Run the bounded LangGraph retrieval loop; final answer generation stays shared."""
    started = monotonic()
    budget = budget or AgentBudget()
    try:
        tools = build_retrieval_tools(
            client=client, catalogue=catalogue, scope=scope, embed=embed,
        )
        graph = build_agent_graph(
            model=model or _default_model(), retrieval_tools=tools, budget=budget,
        )
        invoke_config = {"recursion_limit": budget.max_rounds * 4 + 4}
        callback = langchain_callback()
        if callback is not None:
            invoke_config["callbacks"] = [callback]
        state = graph.invoke({
            "messages": [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=question)],
            "evidence": [],
            "actions": [],
            "fingerprints": [],
            "rounds": 0,
            "tool_calls": 0,
            "planner_tokens": 0,
            "no_progress_rounds": 0,
            "started_at": started,
            "question_scope": None,
            "plan_summary": None,
            "stop_reason": None,
            "should_synthesize": False,
        }, config=invoke_config)
    except Exception as exc:
        logger.exception("Agentic graph failed (%s)", type(exc).__name__)
        return _failed(started, StopReason.PLANNER_FAILURE)

    evidence = list(state.get("evidence", []))
    reason = StopReason(state.get("stop_reason") or StopReason.INSUFFICIENT_EVIDENCE)
    execution = AgentExecutionMetadata(
        question_scope=state.get("question_scope"),
        plan_summary=state.get("plan_summary"),
        stop_reason=reason,
        rounds=state.get("rounds", 0),
        tool_calls=state.get("tool_calls", 0),
        evidence_count=len(evidence),
        planner_tokens=state.get("planner_tokens", 0),
        elapsed_seconds=round(max(0.0, monotonic() - started), 3),
        actions=state.get("actions", []),
    )
    result = AgentRunResult(
        evidence=evidence,
        execution=execution,
        should_synthesize=bool(state.get("should_synthesize")),
    )
    update_span(
        output={"evidence_ids": [row.id for row in evidence],
                "execution": execution.model_dump(mode="json")},
        metadata={"orchestrator": "langgraph", "stop_reason": reason.value,
                  "synthesize": result.should_synthesize},
    )
    return result
