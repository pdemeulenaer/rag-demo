"""LangChain tools exposed to the LangGraph retrieval agent."""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Literal

from langchain_core.tools import BaseTool, tool

from src.api.rag.contracts import (
    EvidenceChunk,
    FederatedRetrievalScope,
    PaperMatch,
    RetrievalBoundary,
    RetrievalScope,
)
from src.api.rag.modes.agentic.policies import narrow_scope
from src.api.rag.tools.chunk_search import search_chunks as scoped_chunk_search
from src.api.rag.tools.neighbor_retrieval import get_neighbors as scoped_neighbors
from src.api.rag.tools.paper_search import search_papers as scoped_paper_search
from src.api.rag.tools.section_retrieval import get_section as scoped_section


QuestionScopeLiteral = Literal[
    "direct", "within_paper", "cross_paper", "metadata_discovery"
]


def _artifact(*, chunks: list[EvidenceChunk] | None = None,
              papers: list[PaperMatch] | None = None) -> dict:
    return {
        "chunks": [row.model_dump(mode="json") for row in chunks or []],
        "papers": [row.model_dump(mode="json") for row in papers or []],
    }


def _content(chunks: list[EvidenceChunk], papers: list[PaperMatch]) -> str:
    payload = {
        "evidence": [{
            "id": row.id, "paper_id": row.paper_id, "build_id": row.build_id,
            "title": row.title, "page": row.page,
            "section_header": row.section_header, "chunk_index": row.chunk_index,
            "text": row.text[:1600],
        } for row in chunks],
        "papers": [{
            "paper_id": row.paper_id, "build_id": row.build_id, "title": row.title,
            "authors": row.authors, "year": row.year,
            "abstract": (row.abstract or "")[:800],
        } for row in papers],
    }
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
        query: str,
        retrieval_mode: Literal["dense", "sparse", "hybrid"] = "hybrid",
        build_ids: list[str] | None = None,
        paper_ids: list[str] | None = None,
        limit: int = 8,
    ) -> tuple[str, dict]:
        """Search chunks with dense semantics, BM25 terms, or fused hybrid retrieval."""
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
    def get_section_tool(build_id: str, paper_id: str, section_header: str,
                         limit: int = 12) -> tuple[str, dict]:
        """Expand an exact section header observed in retrieved evidence."""
        action_scope = (scope.scope_for_build(build_id)
                        if isinstance(scope, FederatedRetrievalScope) else scope)
        chunks = scoped_section(
            client, action_scope, build_id=build_id, paper_id=paper_id,
            section_header=section_header, limit=min(max(limit, 1), 50),
        )
        return _content(chunks, []), _artifact(chunks=chunks)

    @tool("get_neighbors", response_format="content_and_artifact")
    def get_neighbors_tool(build_id: str, paper_id: str, chunk_index: int,
                           before: int = 1, after: int = 1) -> tuple[str, dict]:
        """Expand around a retrieved chunk using its exact stable identifiers."""
        action_scope = (scope.scope_for_build(build_id)
                        if isinstance(scope, FederatedRetrievalScope) else scope)
        chunks = scoped_neighbors(
            client, action_scope, build_id=build_id, paper_id=paper_id,
            chunk_index=chunk_index, before=before, after=after,
        )
        return _content(chunks, []), _artifact(chunks=chunks)

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
