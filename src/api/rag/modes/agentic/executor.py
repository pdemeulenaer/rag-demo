"""Public adapter from the RAG pipeline to the LangGraph retrieval graph."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
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
from src.api.rag.contracts import EvidenceChunk, FederatedRetrievalScope, RetrievalBoundary
from src.api.rag.modes.agentic.contracts import (
    AgentBudget,
    AgentExecutionMetadata,
    AnswerRequirement,
    StopReason,
)
from src.api.rag.modes.agentic.graph import SYSTEM_PROMPT, build_agent_graph
from src.api.rag.modes.agentic.tools import build_retrieval_tools
from src.api.rag.tools.paper_search import resolve_quoted_papers


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentRunResult:
    evidence: list[EvidenceChunk]
    execution: AgentExecutionMetadata
    should_synthesize: bool
    required_paper_ids: tuple[str, ...] = ()
    # Retrieval provenance only: never a citation allowlist.
    evidence_by_requirement: dict[str, tuple[str, ...]] = field(default_factory=dict)
    requirements: list[AnswerRequirement] = field(default_factory=list)


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
            synthesis_policy="hard_stop",
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
def run_agentic(question: str, *, client, catalogue, scope: RetrievalBoundary,
                 embed: Callable[[str], list[float]], budget: AgentBudget | None = None,
                 model=None) -> AgentRunResult:
    """Run bounded retrieval; Agentic answering separately reviews final claims."""
    started = monotonic()
    budget = budget or AgentBudget()
    try:
        child_scopes = scope.scopes if isinstance(scope, FederatedRetrievalScope) else (scope,)
        required_papers = []
        for child_scope in child_scopes:
            required_papers.extend(resolve_quoted_papers(catalogue, child_scope, question))
        required_papers = list({row.build_id: row for row in required_papers}.values())
        required_papers.sort(key=lambda row: (row.title.casefold(), row.build_id))

        tools = build_retrieval_tools(
            client=client, catalogue=catalogue, scope=scope, embed=embed,
        )
        graph = build_agent_graph(
            model=model or _default_model(), retrieval_tools=tools, budget=budget,
        )
        invoke_config = {"recursion_limit": budget.max_rounds * 4 + 8}
        callback = langchain_callback()
        if callback is not None:
            invoke_config["callbacks"] = [callback]
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        if required_papers:
            resolved = "\n".join(
                f"- title={row.title!r}; paper_id={row.paper_id}; "
                f"required_build_id={row.build_id}"
                for row in required_papers
            )
            messages.append(SystemMessage(content=(
                "The catalogue deterministically resolved these full paper titles quoted in "
                "the question. Treat every listed build as required evidence coverage and "
                "search each build independently before finishing:\n" + resolved
            )))
        messages.append(HumanMessage(content=question))
        state = graph.invoke({
            "messages": messages,
            "evidence": [],
            "requirements": [],
            "required_build_ids": [row.build_id for row in required_papers],
            "required_paper_titles": {row.build_id: row.title for row in required_papers},
            "required_paper_ids": [row.paper_id for row in required_papers],
            "actions": [],
            "fingerprints": [],
            "rounds": 0,
            "tool_calls": 0,
            "planner_tokens": 0,
            "next_call_estimated_tokens": None,
            "no_progress_rounds": 0,
            "started_at": started,
            "question_scope": None,
            "plan_summary": None,
            "stop_reason": None,
            "should_synthesize": False,
            "synthesis_policy": "hard_stop",
        }, config=invoke_config)
    except Exception as exc:
        logger.exception("Agentic graph failed (%s)", type(exc).__name__)
        return _failed(started, StopReason.PLANNER_FAILURE)

    evidence = list(state.get("evidence", []))
    actions = list(state.get("actions", []))
    # Catalogue discovery is an intermediate routing step, not answer evidence.
    # Only chunk-producing actions count toward diagnostic search coverage.
    evidence_actions = [action for action in actions if action.tool != "search_papers"]
    requirements = list(state.get("requirements", []))
    need_ids = [row.id for row in requirements]
    citation_groups = {
        need_id: tuple(dict.fromkeys(
            evidence_id
            for action in evidence_actions if action.need_id == need_id
            for evidence_id in action.evidence_ids
        ))
        for need_id in need_ids
    }
    missing_evidence_need_ids = [need_id for need_id, evidence_ids
                                 in citation_groups.items() if not evidence_ids]
    required_build_ids = list(state.get("required_build_ids", []))
    covered_build_ids = {row.build_id for row in evidence}
    missing_required_build_ids = [build_id for build_id in required_build_ids
                                  if build_id not in covered_build_ids]
    reason = StopReason(state.get("stop_reason") or StopReason.INSUFFICIENT_EVIDENCE)
    execution = AgentExecutionMetadata(
        question_scope=state.get("question_scope"),
        plan_summary=state.get("plan_summary"),
        stop_reason=reason,
        synthesis_policy=state.get("synthesis_policy", "hard_stop"),
        rounds=state.get("rounds", 0),
        tool_calls=state.get("tool_calls", 0),
        evidence_count=len(evidence),
        required_paper_count=len(required_build_ids),
        covered_required_paper_count=len(required_build_ids) - len(missing_required_build_ids),
        missing_required_build_ids=missing_required_build_ids,
        required_evidence_need_count=len(need_ids),
        covered_evidence_need_count=len(need_ids) - len(missing_evidence_need_ids),
        missing_evidence_need_ids=missing_evidence_need_ids,
        planner_tokens=state.get("planner_tokens", 0),
        next_call_estimated_tokens=state.get("next_call_estimated_tokens"),
        elapsed_seconds=round(max(0.0, monotonic() - started), 3),
        actions=actions,
        requirements=requirements,
    )
    result = AgentRunResult(
        evidence=evidence,
        execution=execution,
        should_synthesize=bool(state.get("should_synthesize")),
        required_paper_ids=tuple(str(value) for value in state.get("required_paper_ids", [])),
        evidence_by_requirement={
            need_id: evidence_ids for need_id, evidence_ids in citation_groups.items()
            if evidence_ids
        },
        requirements=requirements,
    )
    update_span(
        output={"evidence_ids": [row.id for row in evidence],
                "execution": execution.model_dump(mode="json")},
        metadata={"orchestrator": "langgraph", "stop_reason": reason.value,
                  "synthesize": result.should_synthesize,
                  "required_paper_count": len(required_build_ids),
                  "covered_required_paper_count": (
                      len(required_build_ids) - len(missing_required_build_ids)
                  )},
    )
    return result
