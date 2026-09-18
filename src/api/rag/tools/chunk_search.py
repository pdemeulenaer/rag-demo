"""Scoped Qdrant search with strict evidence identity validation."""
from __future__ import annotations

from src.api.observability.tracing import observe, update_span
from src.api.rag.contracts import EvidenceChunk, RetrievalScope
from src.api.rag.search import search_points
from src.api.rag.tools.evidence import EvidenceScopeError, evidence_from_point


@observe(name="search_chunks", as_type="retriever", capture_input=False, capture_output=False)
def search_chunks(client, scope: RetrievalScope, *, query: str,
                  vector: list[float] | None,
                  limit: int, mode: str) -> list[EvidenceChunk]:
    """Search only explicit builds and fail closed on missing/drifting identity."""
    if limit < 1:
        raise ValueError("Chunk search limit must be positive")
    response = search_points(client, scope.collection, vector, query, limit,
                             mode=mode, scope=scope.qdrant_filter())
    evidence = [evidence_from_point(point, scope) for point in response.points]
    update_span(input={"query": query}, output={"point_ids": [row.id for row in evidence]},
                metadata={"mode": mode, "collection": scope.collection,
                          "scope_kind": scope.kind, "result_count": len(evidence)})
    return evidence
