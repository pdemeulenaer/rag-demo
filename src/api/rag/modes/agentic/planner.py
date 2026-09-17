"""Structured OpenAI planner for the bounded Agentic RAG executor."""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from src.api.core.clients import openai_client
from src.api.core.config import config
from src.api.observability.tracing import observe, update_span
from src.api.rag.contracts import EvidenceChunk, PaperMatch, RetrievalScope
from src.api.rag.modes.agentic.contracts import (
    AgentActionRecord,
    AgentBudget,
    AgentPlan,
    BudgetUsage,
    SufficiencyDecision,
)


PlanValue = TypeVar("PlanValue", bound=BaseModel)


@dataclass(frozen=True)
class PlannerCall(Generic[PlanValue]):
    value: PlanValue
    tokens: int


class AgentPlanner(Protocol):
    """Minimal injectable boundary used by the deterministic executor tests."""

    def plan(self, question: str, scope: RetrievalScope,
             budget: AgentBudget) -> PlannerCall[AgentPlan]: ...

    def assess(self, question: str, plan: AgentPlan, evidence: list[EvidenceChunk],
               papers: list[PaperMatch], actions: list[AgentActionRecord],
               usage: BudgetUsage, budget: AgentBudget) -> PlannerCall[SufficiencyDecision]: ...


PLANNER_SYSTEM = """You are the retrieval planner for a scientific-paper RAG system.
Return only the strict JSON object required by the supplied schema. Produce concise,
auditable plan summaries and evidence requirements, never private chain-of-thought.

You may request only these read-only actions:
- search_papers: resolve title/author/year/abstract metadata to paper and build IDs.
- search_chunks: semantic search; empty build_ids and paper_ids mean the approved corpus.
- get_section: expand one exact section_header observed in retrieved evidence.
- get_neighbors: expand around an observed chunk_index.

Never invent paper IDs, build IDs, section headers, chunk indices or evidence IDs. Use empty
filters when IDs are not known. For a direct question, prefer one focused search_chunks
action. Use search_papers first when a named paper must be resolved. A plan may contain no
mutation, ingestion, deletion, SQL, shell or arbitrary-code action."""


ASSESS_SYSTEM = """You are the evidence sufficiency controller for a scientific-paper RAG
system. Return only the strict JSON object required by the supplied schema. Assess every
declared evidence need. Cite only evidence IDs present in the observations.

Choose synthesize only when every need has directly supporting chunk evidence. Choose
continue only when a different, specific read-only action can fill missing evidence. Choose
abstain when the evidence remains insufficient or another useful action is unavailable.
Paper metadata locates documents but is not itself answer evidence. Never repeat an action,
invent identifiers, expose private chain-of-thought, or request mutation operations."""


def _usage_tokens(response) -> int:
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0
    return int(getattr(usage, "total_tokens", 0) or 0)


def _scope_payload(scope: RetrievalScope) -> dict:
    return {
        "kind": scope.kind,
        "collection": scope.collection,
        "builds": [
            {"build_id": build.build_id, "paper_id": build.paper_id}
            for build in scope.builds
        ],
        "build_ids": list(scope.build_ids),
        "paper_ids": list(scope.paper_ids),
    }


def _evidence_payload(evidence: list[EvidenceChunk]) -> list[dict]:
    return [{
        "id": row.id,
        "build_id": row.build_id,
        "paper_id": row.paper_id,
        "title": row.title,
        "page": row.page,
        "section_header": row.section_header,
        "chunk_index": row.chunk_index,
        "text": row.text[:1600],
    } for row in evidence]


class OpenAIAgentPlanner:
    """Strict structured-output planner; final answer generation remains separate."""

    def __init__(self, model: str | None = None, reasoning_effort: str | None = None,
                 max_completion_tokens: int | None = None):
        self.model = model or config.AGENT_MODEL
        self.reasoning_effort = (
            config.AGENT_REASONING_EFFORT if reasoning_effort is None else reasoning_effort
        )
        self.max_completion_tokens = (
            max_completion_tokens or config.AGENT_MAX_COMPLETION_TOKENS
        )

    def _request(self, response_model: type[PlanValue], system: str,
                 payload: dict) -> PlannerCall[PlanValue]:
        request = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "strict": True,
                    "schema": response_model.model_json_schema(),
                },
            },
            "max_completion_tokens": self.max_completion_tokens,
        }
        supports_reasoning = self.model.lower().startswith(("gpt-5", "o1", "o3", "o4"))
        if (self.reasoning_effort and self.reasoning_effort != "none"
                and supports_reasoning):
            request["reasoning_effort"] = self.reasoning_effort
        last_error: ValidationError | None = None
        tokens = 0
        for _ in range(2):
            response = openai_client().chat.completions.create(**request)
            tokens += _usage_tokens(response)
            try:
                value = response_model.model_validate_json(
                    response.choices[0].message.content
                )
                return PlannerCall(value=value, tokens=tokens)
            except ValidationError as exc:
                last_error = exc
        if last_error is None:  # Defensive: provider returned no parseable response.
            raise RuntimeError("Agent planner returned no parseable response")
        raise last_error

    @observe(name="agentic_plan", as_type="generation", capture_input=False,
             capture_output=False)
    def plan(self, question: str, scope: RetrievalScope,
             budget: AgentBudget) -> PlannerCall[AgentPlan]:
        result = self._request(AgentPlan, PLANNER_SYSTEM, {
            "question": question,
            "approved_corpus": _scope_payload(scope),
            "hard_budget": budget.model_dump(mode="json"),
            "instruction": "Create the smallest useful initial evidence plan.",
        })
        update_span(output={"plan": result.value.model_dump(mode="json")},
                    metadata={"model": self.model, "tokens": result.tokens})
        return result

    @observe(name="agentic_sufficiency", as_type="generation", capture_input=False,
             capture_output=False)
    def assess(self, question: str, plan: AgentPlan, evidence: list[EvidenceChunk],
               papers: list[PaperMatch], actions: list[AgentActionRecord],
               usage: BudgetUsage, budget: AgentBudget) -> PlannerCall[SufficiencyDecision]:
        result = self._request(SufficiencyDecision, ASSESS_SYSTEM, {
            "question": question,
            "plan": plan.model_dump(mode="json"),
            "paper_matches": [row.model_dump(mode="json") for row in papers[-20:]],
            "chunk_evidence": _evidence_payload(evidence),
            "action_history": [row.model_dump(mode="json") for row in actions],
            "budget": budget.model_dump(mode="json"),
            "usage": usage.model_dump(mode="json"),
            "instruction": "Assess evidence and select synthesize, continue, or abstain.",
        })
        update_span(output={"decision": result.value.model_dump(mode="json")},
                    metadata={"model": self.model, "tokens": result.tokens})
        return result
