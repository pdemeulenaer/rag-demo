"""Deterministic, budgeted executor for validated Agentic RAG plans."""
from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Callable

from qdrant_client.models import FieldCondition, Filter, MatchAny

from src.api.observability.tracing import observe, observation, update_span
from src.api.rag.contracts import EvidenceChunk, PaperMatch, RetrievalScope
from src.api.rag.modes.agentic.contracts import (
    AgentActionRecord,
    AgentBudget,
    AgentExecutionMetadata,
    BudgetUsage,
    GetNeighborsAction,
    GetSectionAction,
    SearchChunksAction,
    SearchPapersAction,
    StopReason,
    ToolAction,
    action_fingerprint,
    budget_stop_reason,
    validate_decision_for_plan,
)
from src.api.rag.modes.agentic.planner import AgentPlanner
from src.api.rag.tools.chunk_search import search_chunks
from src.api.rag.tools.neighbor_retrieval import get_neighbors
from src.api.rag.tools.paper_search import search_papers
from src.api.rag.tools.section_retrieval import get_section


@dataclass(frozen=True)
class AgentRunResult:
    evidence: list[EvidenceChunk]
    execution: AgentExecutionMetadata
    should_synthesize: bool


def _narrow_scope(scope: RetrievalScope, build_ids: list[str],
                  paper_ids: list[str]) -> RetrievalScope:
    """Intersect planner filters with the immutable approved corpus boundary."""
    requested_builds = tuple(dict.fromkeys(build_ids)) if build_ids else scope.build_ids
    unknown_builds = set(requested_builds).difference(scope.build_ids)
    if unknown_builds:
        raise ValueError("Agent requested a build outside the approved corpus")

    known_papers = {build.paper_id for build in scope.builds if build.paper_id}
    requested_papers = tuple(dict.fromkeys(paper_ids))
    if requested_papers and known_papers and not set(requested_papers).issubset(known_papers):
        raise ValueError("Agent requested a paper outside the approved corpus")

    selected_builds = tuple(
        build for build in scope.builds if build.build_id in requested_builds
    )
    narrowed_filter = Filter(must=[
        scope.qdrant_filter(),
        FieldCondition(key="build_id", match=MatchAny(any=list(requested_builds))),
    ])
    return RetrievalScope(
        collection=scope.collection,
        build_ids=requested_builds,
        kind=scope.kind,
        paper_ids=requested_papers,
        builds=selected_builds,
        filter_override=narrowed_filter,
    )


def _record(action: ToolAction, *, status: str, result_count: int = 0,
            evidence_ids: list[str] | None = None,
            paper_ids: list[str] | None = None,
            error_type: str | None = None) -> AgentActionRecord:
    return AgentActionRecord(
        action_id=action.action_id,
        need_id=action.need_id,
        tool=action.tool,
        status=status,
        result_count=result_count,
        evidence_ids=evidence_ids or [],
        paper_ids=paper_ids or [],
        error_type=error_type,
    )


def _execute_action(action: ToolAction, *, client, catalogue, scope: RetrievalScope,
                    embed: Callable[[str], list[float]]) -> tuple[list[EvidenceChunk],
                                                                  list[PaperMatch]]:
    if isinstance(action, SearchPapersAction):
        return [], search_papers(
            catalogue,
            scope,
            title=action.title,
            author=action.author,
            year=action.year,
            terms=action.terms,
            source=action.source,
            limit=action.limit,
        )
    if isinstance(action, SearchChunksAction):
        action_scope = _narrow_scope(scope, action.build_ids, action.paper_ids)
        return search_chunks(
            client,
            action_scope,
            query=action.query,
            vector=embed(action.query),
            limit=action.limit,
            mode=action.retrieval_mode,
        ), []
    if isinstance(action, GetSectionAction):
        return get_section(
            client,
            scope,
            build_id=action.build_id,
            paper_id=action.paper_id,
            section_header=action.section_header,
            limit=action.limit,
        ), []
    if isinstance(action, GetNeighborsAction):
        return get_neighbors(
            client,
            scope,
            build_id=action.build_id,
            paper_id=action.paper_id,
            chunk_index=action.chunk_index,
            before=action.before,
            after=action.after,
        ), []
    raise TypeError("Unsupported validated agent action")


def _metadata(plan, stop_reason: StopReason, usage: BudgetUsage,
              started: float, actions: list[AgentActionRecord]) -> AgentExecutionMetadata:
    return AgentExecutionMetadata(
        question_scope=plan.question_scope if plan is not None else None,
        plan_summary=plan.plan_summary if plan is not None else None,
        stop_reason=stop_reason,
        rounds=usage.rounds,
        tool_calls=usage.tool_calls,
        evidence_count=usage.evidence_chunks,
        planner_tokens=usage.planner_tokens,
        elapsed_seconds=round(max(0.0, monotonic() - started), 3),
        actions=actions,
    )


@observe(name="agentic_retrieval", capture_input=False, capture_output=False)
def run_agentic(question: str, *, client, catalogue, scope: RetrievalScope,
                 planner: AgentPlanner, embed: Callable[[str], list[float]],
                 budget: AgentBudget | None = None) -> AgentRunResult:
    """Plan and retrieve evidence within hard limits; never synthesize an answer."""
    budget = budget or AgentBudget()
    started = monotonic()
    usage = BudgetUsage()
    evidence_by_id: dict[str, EvidenceChunk] = {}
    papers_by_build: dict[str, PaperMatch] = {}
    records: list[AgentActionRecord] = []
    fingerprints: set[str] = set()
    plan = None

    def finish(reason: StopReason, synthesize: bool = False) -> AgentRunResult:
        execution = _metadata(plan, reason, usage, started, records)
        update_span(
            output={"evidence_ids": list(evidence_by_id),
                    "execution": execution.model_dump(mode="json")},
            metadata={"stop_reason": reason.value, "synthesize": synthesize},
        )
        return AgentRunResult(
            evidence=list(evidence_by_id.values()),
            execution=execution,
            should_synthesize=synthesize,
        )

    try:
        planned = planner.plan(question, scope, budget)
        plan = planned.value
        usage.planner_tokens += planned.tokens
    except Exception:  # Provider/validation details remain in the trace, not the public API.
        return finish(StopReason.PLANNER_FAILURE)

    initial_stop = budget_stop_reason(
        budget,
        usage.model_copy(update={"elapsed_seconds": monotonic() - started}),
    )
    if initial_stop is not None:
        return finish(initial_stop)

    pending = plan.initial_actions
    no_progress_rounds = 0
    while pending:
        if usage.rounds >= budget.max_rounds:
            return finish(StopReason.MAX_ROUNDS)
        usage.rounds += 1
        new_information = 0
        returned_information = 0
        executed = 0
        errors = 0
        duplicates = 0

        for action in pending:
            if usage.tool_calls >= budget.max_tool_calls:
                records.append(_record(action, status="skipped",
                                       error_type="ToolCallBudgetExhausted"))
                continue
            if monotonic() - started >= budget.max_elapsed_seconds:
                records.append(_record(action, status="skipped",
                                       error_type="TimeBudgetExhausted"))
                continue
            fingerprint = action_fingerprint(action)
            if fingerprint in fingerprints:
                duplicates += 1
                records.append(_record(action, status="skipped",
                                       error_type="RepeatedAction"))
                continue
            fingerprints.add(fingerprint)
            usage.tool_calls += 1
            executed += 1
            try:
                with observation(
                    name=f"agentic_tool_{action.tool}",
                    as_type="tool",
                    input=action.model_dump(mode="json"),
                ) as tool_span:
                    chunks, papers = _execute_action(
                        action, client=client, catalogue=catalogue,
                        scope=scope, embed=embed,
                    )
                    remaining = budget.max_evidence_chunks - len(evidence_by_id)
                    returned_information += len(chunks) + len(papers)
                    accepted = []
                    for chunk in chunks:
                        if chunk.id in evidence_by_id:
                            continue
                        if remaining <= 0:
                            break
                        evidence_by_id[chunk.id] = chunk
                        accepted.append(chunk)
                        remaining -= 1
                    new_information += len(accepted)
                    for paper in papers:
                        if paper.build_id not in papers_by_build:
                            new_information += 1
                        papers_by_build[paper.build_id] = paper
                    record = _record(
                        action,
                        status="success",
                        result_count=len(chunks) + len(papers),
                        evidence_ids=[row.id for row in accepted],
                        paper_ids=list(dict.fromkeys(
                            [row.paper_id for row in accepted]
                            + [row.paper_id for row in papers]
                        )),
                    )
                    records.append(record)
                    if tool_span is not None:
                        tool_span.update(output=record.model_dump(mode="json"))
            except Exception as exc:
                errors += 1
                records.append(_record(action, status="error",
                                       error_type=type(exc).__name__))

        usage.evidence_chunks = len(evidence_by_id)
        usage.elapsed_seconds = monotonic() - started
        if executed == 0 and duplicates:
            return finish(StopReason.REPEATED_ACTION)
        if executed and errors == executed:
            return finish(StopReason.TOOL_FAILURE)

        if (returned_information and new_information == 0
                and usage.evidence_chunks < budget.max_evidence_chunks):
            return finish(StopReason.NO_PROGRESS)
        no_progress_rounds = no_progress_rounds + 1 if new_information == 0 else 0
        if no_progress_rounds >= 2:
            return finish(StopReason.NO_PROGRESS)
        if usage.elapsed_seconds >= budget.max_elapsed_seconds:
            return finish(StopReason.TIME_BUDGET)

        try:
            assessed = planner.assess(
                question,
                plan,
                list(evidence_by_id.values()),
                list(papers_by_build.values()),
                records,
                usage,
                budget,
            )
            usage.planner_tokens += assessed.tokens
            decision = assessed.value
            validate_decision_for_plan(plan, decision, set(evidence_by_id))
        except Exception:
            return finish(StopReason.PLANNER_FAILURE)

        usage.elapsed_seconds = monotonic() - started
        if usage.elapsed_seconds >= budget.max_elapsed_seconds:
            return finish(StopReason.TIME_BUDGET)
        if usage.planner_tokens >= budget.max_planner_tokens:
            return finish(StopReason.TOKEN_BUDGET)
        if decision.decision == "synthesize":
            return finish(StopReason.SUFFICIENT, synthesize=True)
        if decision.decision == "abstain":
            return finish(decision.stop_reason or StopReason.INSUFFICIENT_EVIDENCE)

        stop = budget_stop_reason(budget, usage)
        if stop is not None:
            return finish(stop)
        pending = decision.next_actions

    return finish(StopReason.INSUFFICIENT_EVIDENCE)
