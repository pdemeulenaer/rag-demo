"""LangGraph orchestration for bounded, tool-calling Agentic retrieval."""
from __future__ import annotations

import logging
from time import monotonic

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import ValidationError

from src.api.rag.contracts import EvidenceChunk
from src.api.rag.modes.agentic.contracts import (
    AgentActionRecord,
    AgentBudget,
    AnswerRequirement,
    StopReason,
)
from src.api.rag.modes.agentic.policies import action_fingerprint
from src.api.rag.modes.agentic.state import AgentState
from src.api.rag.modes.agentic.tools import TERMINAL_TOOLS, define_requirements


logger = logging.getLogger(__name__)
RETRIEVAL_TOOL_NAMES = {"search_papers", "search_chunks", "get_section", "get_neighbors"}
TERMINAL_TOOL_NAMES = {"finish_with_evidence", "abstain"}
QUESTION_SCOPES = {"direct", "within_paper", "cross_paper", "metadata_discovery"}

SYSTEM_PROMPT = """You are a retrieval agent for a scientific-paper RAG system.
Use the supplied read-only tools to gather answer evidence from the approved corpus.

Rules:
- Your FIRST response must call define_requirements alone. Create one requirement per
  independently answerable subquestion or requested metric. Keep both ends of a range or
  comparison together in one requirement; do not create separate requirements for its
  endpoints, units, paper identity, or other context already supplied by the question.
  Preserve all requested values, units, uncertainties, assumptions, and comparisons within
  the relevant requirement. Avoid duplicates and include every actual part of the question.
- The graph assigns stable r1, r2, ... IDs. Use only these IDs as need_id on retrieval calls.
  Reformulations, metadata lookups and expansion reuse an existing ID. The list cannot grow
  with tool history. A chunk found for any need may support any other need.
- Each search_chunks query must target exactly one atomic need and contain only the terms
  useful for that fact. Never submit the entire multi-part user question as one search query.
- If one paper is asked for several distinct measurements, issue separate focused searches
  for those measurements. Calls for independent needs may run in parallel.
- For a broad factual question, start with one focused hybrid search_chunks call.
- Use sparse search for exact identifiers, acronyms, catalogue numbers and named objects;
  use dense search for conceptual paraphrases; use hybrid when both signals are useful.
- Use search_papers only to resolve a named paper or metadata constraint.
- The system may provide authoritative `required_build_id` values for paper titles quoted in
  the question. When it does, issue one focused search_chunks call per required build (parallel
  calls are allowed) and collect evidence from every required build before finishing.
- Call get_section/get_neighbors only with exact identifiers seen in tool results.
- search_chunks returns compact previews. text_truncated=true means text was hidden, not
  that the evidence is absent. Read a promising hit with get_neighbors before=0, after=0,
  or get_section, before searching elsewhere for a detail potentially in that hit.
- get_neighbors permits only 0–5 neighbours per side. Expansion exposes full chunk text
  within a bounded response budget; inspect text_truncated and narrow the window if needed.
- Once the requested facts are explicit in the evidence, finish; do not expand just to
  reconfirm the same answer.
- Never invent identifiers, repeat an identical call, or request mutation/code execution.
- Tool metadata alone is not answer evidence; answers require retrieved chunks.
- After every retrieval round, check every atomic need against the returned text. Reformulate
  and search again for unsupported needs; paper-level coverage alone is not sufficient.
- When chunks provide potentially useful answer evidence, call finish_with_evidence with a
  concise public summary. The reviewed grounded generator, not this planner, makes the final
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


def _missing_required_builds(state: AgentState) -> list[str]:
    covered = {row.build_id for row in state.get("evidence", [])}
    return [build_id for build_id in state.get("required_build_ids", [])
            if build_id not in covered]


def _missing_evidence_needs(state: AgentState) -> list[str]:
    """Return atomic retrieval needs for which no answer evidence was retained."""
    evidence_by_need: dict[str, set[str]] = {
        row.id: set() for row in state.get("requirements", [])
    }
    for action in state.get("actions", []):
        if action.tool == "search_papers":
            continue
        need_id = action.need_id
        evidence_by_need.setdefault(need_id, set()).update(action.evidence_ids)
    return sorted(need_id for need_id, evidence_ids in evidence_by_need.items()
                  if not evidence_ids)


def _unsearched_requirements(state: AgentState, requirements=None):
    """Requirements with no initial chunk-search attempt yet."""
    requirements = requirements if requirements is not None else state.get("requirements", [])
    searched = {row.need_id for row in state.get("actions", [])
                if row.tool == "search_chunks"}
    return [row for row in requirements if row.id not in searched]


def _terminate(state: AgentState, reason: StopReason, *, summary: str | None = None) -> dict:
    """Stop retrieval, but preserve already collected evidence for grounded synthesis."""
    use_evidence = (
        bool(state.get("evidence"))
        and reason in EVIDENCE_FALLBACK_REASONS
    )
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


def _recorded_query(tool_name: str, args: dict) -> str | None:
    """Return the bounded, non-reasoning lookup text used by a retrieval tool."""
    if tool_name == "search_chunks":
        value = args.get("query")
    elif tool_name == "search_papers":
        parts = []
        for key in ("title", "author", "year", "terms", "source"):
            if args.get(key) not in (None, "", []):
                parts.append(f"{key}={args[key]}")
        value = "; ".join(parts) or "catalogue search"
    elif tool_name == "get_section":
        value = f"section_header={args.get('section_header')}"
    elif tool_name == "get_neighbors":
        value = (
            f"chunk_index={args.get('chunk_index')}; before={args.get('before', 1)}; "
            f"after={args.get('after', 1)}"
        )
    else:
        return None
    normalized = " ".join(str(value).split())
    return normalized[:500] or None


def _route_guard(state: AgentState) -> str:
    if state.get("stop_reason"):
        return END
    return "agent" if isinstance(state["messages"][-1], ToolMessage) else "tools"


def _route_collect(state: AgentState) -> str:
    return END if state.get("stop_reason") else "agent"


def build_agent_graph(*, model, retrieval_tools: list, budget: AgentBudget):
    """Compile one request-scoped graph with native LangChain tool schemas."""
    # Enforce the first action through the native provider tool protocol, not just prose.
    definition_model = model.bind_tools(
        [define_requirements], tool_choice="define_requirements", parallel_tool_calls=False)
    bound_model = model.bind_tools([define_requirements, *retrieval_tools, *TERMINAL_TOOLS])

    def schedule_requirement_searches(state: AgentState, requirements, *, defer_calls=(),
                                      prefix_messages=()):
        """Guarantee one focused baseline search for every decomposed need first."""
        pending = _unsearched_requirements(state, requirements)
        if not pending:
            return None
        if monotonic() - state["started_at"] >= budget.max_elapsed_seconds:
            return {**_terminate(state, StopReason.TIME_BUDGET),
                    "messages": list(prefix_messages)}
        if state.get("planner_tokens", 0) >= budget.max_planner_tokens:
            return {**_terminate(state, StopReason.TOKEN_BUDGET),
                    "messages": list(prefix_messages)}
        if state.get("rounds", 0) >= budget.max_rounds:
            return {**_terminate(state, StopReason.MAX_ROUNDS),
                    "messages": list(prefix_messages)}
        if len(state.get("evidence", [])) >= budget.max_evidence_chunks:
            return {**_terminate(state, StopReason.EVIDENCE_BUDGET),
                    "messages": list(prefix_messages)}

        available = budget.max_tool_calls - state.get("tool_calls", 0)
        if available <= 0:
            return {**_terminate(state, StopReason.TOOL_CALL_BUDGET),
                    "messages": list(prefix_messages)}
        selected = pending[:available]
        generated = []
        new_fingerprints = []
        existing = set(state.get("fingerprints", []))
        for index, requirement in enumerate(selected):
            args = {
                "need_id": requirement.id,
                "query": requirement.description[:500],
                "retrieval_mode": "hybrid",
                "build_ids": [],
                "paper_ids": [],
                "limit": 8,
            }
            fingerprint = action_fingerprint("search_chunks", args)
            if fingerprint not in existing:
                existing.add(fingerprint)
                new_fingerprints.append(fingerprint)
            generated.append({
                "name": "search_chunks",
                "args": args,
                "id": f"coverage_{requirement.id}_{state.get('tool_calls', 0) + index + 1}",
                "type": "tool_call",
            })
        if not generated:
            return {**_terminate(state, StopReason.REPEATED_ACTION),
                    "messages": list(prefix_messages)}

        deferred = [ToolMessage(
            name=call["name"], tool_call_id=call["id"],
            content="Deferred until each atomic evidence need has received its initial search.",
        ) for call in defer_calls]
        scheduled = AIMessage(content="", tool_calls=generated)
        logger.info("Agentic coverage-first search scheduled %d of %d pending needs",
                    len(generated), len(pending))
        return {
            "messages": [*prefix_messages, *deferred, scheduled],
            "fingerprints": [*state.get("fingerprints", []), *new_fingerprints],
            "plan_summary": "Running a focused baseline search for each atomic evidence need.",
        }

    def call_agent(state: AgentState) -> dict:
        try:
            active_model = bound_model if state.get("requirements") else definition_model
            response = active_model.invoke(state["messages"])
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
        if state.get("requirements"):
            pending_searches = _unsearched_requirements(state)
            if pending_searches and len(state.get("requirements", [])) > 1:
                update = schedule_requirement_searches(
                    state, state["requirements"], defer_calls=calls,
                )
                if update is not None:
                    return update
        if not calls:
            return _terminate(
                state, StopReason.PLANNER_FAILURE,
                summary="The agent did not select a valid retrieval or terminal tool.",
            )

        definitions = [call for call in calls if call["name"] == "define_requirements"]
        if definitions:
            try:
                if state.get("requirements") or len(calls) != 1:
                    raise ValueError("Requirements must be defined once, before retrieval")
                if monotonic() - state["started_at"] >= budget.max_elapsed_seconds:
                    return _terminate(state, StopReason.TIME_BUDGET)
                if state.get("planner_tokens", 0) >= budget.max_planner_tokens:
                    return _terminate(state, StopReason.TOKEN_BUDGET)
                args = define_requirements.args_schema.model_validate(definitions[0].get("args") or {})
                requirements = []
                seen_descriptions = set()
                for description in args.descriptions:
                    normalized = " ".join(description.casefold().split())
                    if not normalized:
                        raise ValueError("empty_requirement")
                    if normalized in seen_descriptions:
                        raise ValueError("duplicate_requirements")
                    seen_descriptions.add(normalized)
                    requirements.append(AnswerRequirement(
                        id=f"r{len(requirements) + 1}", description=description.strip()))
                if not requirements:
                    raise ValueError("empty_requirements")
            except ValidationError as error:
                # Report validation codes only. Do not leak model inputs into logs/results.
                codes = sorted({str(item.get("type", "invalid"))
                                for item in error.errors(include_input=False)})
                logger.warning("Agentic requirement definition rejected (codes=%s)", codes)
                return _terminate(
                    state, StopReason.PLANNER_FAILURE,
                    summary="Question requirements failed validation: " + ", ".join(codes),
                )
            except ValueError as error:
                code = str(error)[:80] or "invalid_requirements"
                logger.warning("Agentic requirement definition rejected (code=%s)", code)
                return _terminate(
                    state, StopReason.PLANNER_FAILURE,
                    summary="Question requirements were invalid (" + code + ").",
                )
            definition_reply = ToolMessage(
                name="define_requirements", tool_call_id=definitions[0]["id"],
                content="Use these fixed requirement IDs for all searches: " + str(
                    [row.model_dump() for row in requirements]),
            )
            if len(requirements) > 1:
                seeded_state = {**state, "requirements": requirements}
                update = schedule_requirement_searches(
                    seeded_state, requirements, prefix_messages=[definition_reply],
                )
                if update is not None:
                    update["requirements"] = requirements
                    return update
            return {"requirements": requirements, "messages": [definition_reply]}
        if not state.get("requirements"):
            return _terminate(state, StopReason.PLANNER_FAILURE,
                              summary="Question requirements must be defined before retrieval.")

        terminal = [call for call in calls if call["name"] in TERMINAL_TOOL_NAMES]
        retrieval = [call for call in calls if call["name"] in RETRIEVAL_TOOL_NAMES]
        unknown = [call for call in calls
                   if call["name"] not in TERMINAL_TOOL_NAMES | RETRIEVAL_TOOL_NAMES]
        if unknown or (terminal and (retrieval or len(terminal) != 1)):
            return _terminate(
                state, StopReason.PLANNER_FAILURE,
                summary="The agent selected an invalid combination of tools.",
            )
        known_need_ids = {row.id for row in state["requirements"]}
        if retrieval and any((call.get("args") or {}).get("need_id") not in known_need_ids
                             for call in retrieval):
            return _terminate(
                state, StopReason.PLANNER_FAILURE,
                summary="Retrieval actions must use a defined question requirement ID.",
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
            missing_required = _missing_required_builds(state)
            missing_needs = _missing_evidence_needs(state)
            can_finish = (
                call["name"] == "finish_with_evidence"
                and bool(state.get("evidence"))
                and not missing_required
                and not missing_needs
            )
            if can_finish:
                return {
                    "stop_reason": StopReason.SUFFICIENT.value,
                    "should_synthesize": True,
                    "synthesis_policy": "model_finish",
                    "question_scope": scope,
                    "plan_summary": summary,
                }
            if call["name"] == "finish_with_evidence" and missing_required:
                summary = (
                    "The agent attempted to finish before retrieving every explicitly named "
                    f"paper ({len(missing_required)} missing)."
                )
            elif call["name"] == "finish_with_evidence" and missing_needs:
                summary = (
                    "The agent attempted to finish before finding evidence for every atomic "
                    f"need ({len(missing_needs)} missing)."
                )
            update = _terminate(state, StopReason.INSUFFICIENT_EVIDENCE, summary=summary)
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
            call_args = call.get("args") or {}
            artifact = message.artifact if isinstance(message.artifact, dict) else {}
            is_error = getattr(message, "status", "success") == "error" or not artifact
            accepted: list[EvidenceChunk] = []
            action_evidence: list[EvidenceChunk] = []
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
                    if chunk.id in evidence_by_id:
                        action_evidence.append(evidence_by_id[chunk.id])
                        paper_ids.append(chunk.paper_id)
                        continue
                    if remaining <= 0:
                        continue
                    evidence_by_id[chunk.id] = chunk
                    accepted.append(chunk)
                    action_evidence.append(chunk)
                    paper_ids.append(chunk.paper_id)
                    new_information += 1
                    remaining -= 1
            records.append(AgentActionRecord(
                action_id=str(message.tool_call_id),
                need_id=str(call_args.get("need_id") or "unassigned")[:128],
                tool=name,
                query=_recorded_query(name, call_args),
                status="error" if is_error else "success",
                result_count=result_count,
                # Keep the evidence returned for this need even when another need
                # already retained the same point. This is diagnostic search
                # coverage, not a final-answer citation constraint.
                evidence_ids=list(dict.fromkeys(row.id for row in action_evidence)),
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
        elif _unsearched_requirements(update) and len(update.get("requirements", [])) > 1:
            if update["rounds"] >= budget.max_rounds:
                update.update(_terminate(update, StopReason.MAX_ROUNDS))
            elif update["tool_calls"] >= budget.max_tool_calls:
                update.update(_terminate(update, StopReason.TOOL_CALL_BUDGET))
            elif update.get("planner_tokens", 0) >= budget.max_planner_tokens:
                update.update(_terminate(update, StopReason.TOKEN_BUDGET))
            elif len(update.get("evidence", [])) >= budget.max_evidence_chunks:
                update.update(_terminate(update, StopReason.EVIDENCE_BUDGET))
            elif monotonic() - state["started_at"] >= budget.max_elapsed_seconds:
                update.update(_terminate(update, StopReason.TIME_BUDGET))
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
    graph.add_conditional_edges("guard", _route_guard, {"tools": "tools", "agent": "agent", END: END})
    graph.add_edge("tools", "collect")
    graph.add_conditional_edges("collect", _route_collect, {"agent": "agent", END: END})
    return graph.compile()
