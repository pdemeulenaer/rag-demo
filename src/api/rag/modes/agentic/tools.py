"""LangChain tools exposed to the LangGraph retrieval agent."""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Annotated, Literal

from langchain_core.tools import BaseTool, tool
from pydantic import Field

from src.api.rag.contracts import (
    EvidenceChunk,
    FederatedRetrievalScope,
    PaperMatch,
    RetrievalBoundary,
    RetrievalScope,
)
from src.api.rag.modes.agentic.policies import narrow_scope
from src.api.rag.tools.chunk_search import search_chunks as scoped_chunk_search
from src.api.rag.tools.neighbor_retrieval import (
    MAX_NEIGHBORS_PER_SIDE,
    get_neighbors as scoped_neighbors,
)
from src.api.rag.tools.paper_search import search_papers as scoped_paper_search
from src.api.rag.tools.section_retrieval import get_section as scoped_section


QuestionScopeLiteral = Literal[
    "direct", "within_paper", "cross_paper", "metadata_discovery"
]
PLANNER_CHUNK_PREVIEW_CHARS = 700
PLANNER_ABSTRACT_PREVIEW_CHARS = 400
# Text-only budget per expansion response; artifacts keep the original full chunks.
PLANNER_EXPANSION_TEXT_CHARS = 12000
NeighborCount = Annotated[int, Field(strict=True, ge=0, le=MAX_NEIGHBORS_PER_SIDE)]
ChunkIndex = Annotated[int, Field(strict=True, ge=0)]
EvidenceNeedId = Annotated[str, Field(
    min_length=1,
    max_length=128,
    description="Graph-assigned requirement ID (r1, r2, etc.) from define_requirements; never invent a new ID.",
)]
SearchQuery = Annotated[str, Field(
    min_length=1,
    max_length=500,
    description="Focused query for one atomic evidence need, not the full user question.",
)]


def _artifact(*, chunks: list[EvidenceChunk] | None = None,
              papers: list[PaperMatch] | None = None) -> dict:
    return {
        "chunks": [row.model_dump(mode="json") for row in chunks or []],
        "papers": [row.model_dump(mode="json") for row in papers or []],
    }


def _content(chunks: list[EvidenceChunk], papers: list[PaperMatch], *,
             expanded: bool = False, anchor_index: int | None = None) -> str:
    # Read the requested anchor first so preceding neighbours cannot consume its budget.
    # Preserve the original document ordering in the response and artifact.
    texts = {}
    remaining = PLANNER_EXPANSION_TEXT_CHARS
    priority = sorted(range(len(chunks)), key=lambda i: (
        chunks[i].chunk_index != anchor_index if anchor_index is not None else False, i))
    for index in priority:
        text = chunks[index].text
        texts[index] = text[:remaining] if expanded else text[:PLANNER_CHUNK_PREVIEW_CHARS]
        if expanded:
            remaining -= len(texts[index])
    payload = {
        "text_mode": "expanded" if expanded else "preview",
        "evidence": [{
            "id": row.id, "paper_id": row.paper_id, "build_id": row.build_id,
            "title": row.title, "page": row.page,
            "section_header": row.section_header, "chunk_index": row.chunk_index,
            "text": texts[index],
            "text_truncated": len(texts[index]) < len(row.text),
            "text_chars": len(row.text),
        } for index, row in enumerate(chunks)],
        "papers": [{
            "paper_id": row.paper_id, "build_id": row.build_id, "title": row.title,
            "authors": row.authors, "year": row.year,
            "abstract": (row.abstract or "")[:PLANNER_ABSTRACT_PREVIEW_CHARS],
        } for row in papers],
    }
    if expanded:
        payload["text_budget_chars"] = PLANNER_EXPANSION_TEXT_CHARS
    return json.dumps(payload, ensure_ascii=False)


def _scopes(scope: RetrievalBoundary) -> tuple[RetrievalScope, ...]:
    return scope.scopes if isinstance(scope, FederatedRetrievalScope) else (scope,)


def _merge_chunks(rows: list[EvidenceChunk], limit: int) -> list[EvidenceChunk]:
    rows.sort(key=lambda row: (
        -(row.score if row.score is not None else float("-inf")),
        row.collection,
        row.id,
    ))
    return rows[:limit]


def _action_scopes(scope: RetrievalBoundary, build_ids: list[str] | None,
                   paper_ids: list[str] | None) -> list[RetrievalScope]:
    requested_builds = set(build_ids or scope.build_ids)
    if requested_builds.difference(scope.build_ids):
        raise ValueError("Agent requested a build outside the approved corpus")
    requested_papers = set(paper_ids or ())
    known_papers = {build.paper_id for build in scope.builds if build.paper_id}
    if requested_papers and known_papers and requested_papers.difference(known_papers):
        raise ValueError("Agent requested a paper outside the approved corpus")

    selected = []
    for child in _scopes(scope):
        child_builds = [value for value in child.build_ids if value in requested_builds]
        if not child_builds:
            continue
        child_known_papers = {build.paper_id for build in child.builds if build.paper_id}
        child_papers = [value for value in paper_ids or ()
                        if not child_known_papers or value in child_known_papers]
        if requested_papers and child_known_papers and not child_papers:
            continue
        selected.append(narrow_scope(child, child_builds, child_papers))
    return selected


def build_retrieval_tools(*, client, catalogue, scope: RetrievalBoundary,
                          embed: Callable[[str], list[float]]) -> list[BaseTool]:
    """Build request-scoped, read-only tools bound to an approved corpus."""

    @tool("search_papers", response_format="content_and_artifact")
    def search_papers_tool(
        need_id: EvidenceNeedId,
        title: str | None = None,
        author: str | None = None,
        year: int | None = None,
        terms: list[str] | None = None,
        source: Literal["arxiv", "uploads"] | None = None,
        limit: int = 10,
    ) -> tuple[str, dict]:
        """Find papers by catalogue metadata. Combine supplied filters with AND."""
        bounded_limit = min(max(limit, 1), 10)
        papers = []
        for child in _scopes(scope):
            papers.extend(scoped_paper_search(
                catalogue, child, title=title, author=author, year=year,
                terms=terms or (), source=source, limit=bounded_limit,
            ))
        papers.sort(key=lambda row: (row.title.casefold(), row.build_id))
        papers = papers[:bounded_limit]
        return _content([], papers), _artifact(papers=papers)

    @tool("search_chunks", response_format="content_and_artifact")
    def search_chunks_tool(
        need_id: EvidenceNeedId,
        query: SearchQuery,
        retrieval_mode: Literal["dense", "sparse", "hybrid"] = "hybrid",
        build_ids: list[str] | None = None,
        paper_ids: list[str] | None = None,
        limit: int = 8,
    ) -> tuple[str, dict]:
        """Search dense/BM25/hybrid chunks. Text is a 700-character preview; expand truncated hits."""
        bounded_limit = min(max(limit, 1), 20)
        vector = None if retrieval_mode == "sparse" else embed(query)
        chunks = []
        for action_scope in _action_scopes(scope, build_ids, paper_ids):
            chunks.extend(scoped_chunk_search(
                client, action_scope, query=query, vector=vector,
                limit=bounded_limit, mode=retrieval_mode,
            ))
        chunks = _merge_chunks(chunks, bounded_limit)
        return _content(chunks, []), _artifact(chunks=chunks)

    @tool("get_section", response_format="content_and_artifact")
    def get_section_tool(need_id: EvidenceNeedId, build_id: str, paper_id: str,
                         section_header: str,
                         limit: int = 12) -> tuple[str, dict]:
        """Read an observed section with full chunk text, capped at 12000 text characters total."""
        action_scope = (scope.scope_for_build(build_id)
                        if isinstance(scope, FederatedRetrievalScope) else scope)
        chunks = scoped_section(
            client, action_scope, build_id=build_id, paper_id=paper_id,
            section_header=section_header, limit=min(max(limit, 1), 50),
        )
        return _content(chunks, [], expanded=True), _artifact(chunks=chunks)

    @tool("get_neighbors", response_format="content_and_artifact")
    def get_neighbors_tool(need_id: EvidenceNeedId, build_id: str, paper_id: str,
                           chunk_index: ChunkIndex,
                           before: NeighborCount = 1, after: NeighborCount = 1) -> tuple[str, dict]:
        """Read an observed chunk and 0–5 neighbours per side; 0/0 reads only the anchor.

        Full chunk text up to 12000 characters total; the anchor has budget priority.
        Check text_truncated on each returned chunk. Use exact observed identifiers.
        """
        action_scope = (scope.scope_for_build(build_id)
                        if isinstance(scope, FederatedRetrievalScope) else scope)
        chunks = scoped_neighbors(
            client, action_scope, build_id=build_id, paper_id=paper_id,
            chunk_index=chunk_index, before=before, after=after,
        )
        return _content(chunks, [], expanded=True, anchor_index=chunk_index), _artifact(chunks=chunks)

    return [search_papers_tool, search_chunks_tool, get_section_tool, get_neighbors_tool]


@tool("finish_with_evidence")
def finish_with_evidence(summary: str, question_scope: QuestionScopeLiteral) -> str:
    """Finish retrieval when accumulated chunk evidence can answer the question."""
    return summary


@tool("abstain")
def abstain(summary: str, question_scope: QuestionScopeLiteral) -> str:
    """Stop when indexed evidence cannot safely answer the question."""
    return summary


TERMINAL_TOOLS = [finish_with_evidence, abstain]


@tool("define_requirements")
def define_requirements(
    descriptions: Annotated[list[Annotated[str, Field(min_length=1, max_length=2000)]],
                      Field(min_length=1, max_length=20)],
) -> str:
    """Declare one need per independently answerable question part or requested metric.

    The graph assigns immutable r1, r2, ... IDs. Repeated searches reuse those IDs;
    retrieval actions cannot add answer requirements. Keep requested comparison/range
    endpoints together and include their units/qualifiers; do not create metadata-only needs.
    """
    return "Requirements are registered by the graph guard."
