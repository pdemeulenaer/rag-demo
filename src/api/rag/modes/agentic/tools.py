"""LangChain tools exposed to the LangGraph retrieval agent."""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Literal

from langchain_core.tools import BaseTool, tool

from src.api.rag.contracts import EvidenceChunk, PaperMatch, RetrievalScope
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


def build_retrieval_tools(*, client, catalogue, scope: RetrievalScope,
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
        papers = scoped_paper_search(
            catalogue, scope, title=title, author=author, year=year,
            terms=terms or (), source=source, limit=min(max(limit, 1), 10),
        )
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
        action_scope = narrow_scope(scope, build_ids, paper_ids)
        vector = None if retrieval_mode == "sparse" else embed(query)
        chunks = scoped_chunk_search(
            client, action_scope, query=query, vector=vector,
            limit=min(max(limit, 1), 20), mode=retrieval_mode,
        )
        return _content(chunks, []), _artifact(chunks=chunks)

    @tool("get_section", response_format="content_and_artifact")
    def get_section_tool(build_id: str, paper_id: str, section_header: str,
                         limit: int = 12) -> tuple[str, dict]:
        """Expand an exact section header observed in retrieved evidence."""
        chunks = scoped_section(
            client, scope, build_id=build_id, paper_id=paper_id,
            section_header=section_header, limit=min(max(limit, 1), 50),
        )
        return _content(chunks, []), _artifact(chunks=chunks)

    @tool("get_neighbors", response_format="content_and_artifact")
    def get_neighbors_tool(build_id: str, paper_id: str, chunk_index: int,
                           before: int = 1, after: int = 1) -> tuple[str, dict]:
        """Expand around a retrieved chunk using its exact stable identifiers."""
        chunks = scoped_neighbors(
            client, scope, build_id=build_id, paper_id=paper_id,
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
