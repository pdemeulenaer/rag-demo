"""Scoped Qdrant search with strict evidence identity validation."""
from __future__ import annotations

from src.api.observability.tracing import observe, update_span
from src.api.rag.contracts import EvidenceChunk, RetrievalScope
from src.api.rag.search import search_points


class EvidenceScopeError(ValueError):
    """Qdrant returned a point whose identity is outside the SQL-selected scope."""


def _optional_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


@observe(name="search_chunks", as_type="retriever", capture_input=False, capture_output=False)
def search_chunks(client, scope: RetrievalScope, *, query: str, vector: list[float],
                  limit: int, mode: str) -> list[EvidenceChunk]:
    """Search only explicit builds and fail closed on missing/drifting identity."""
    if limit < 1:
        raise ValueError("Chunk search limit must be positive")
    response = search_points(client, scope.collection, vector, query, limit,
                             mode=mode, scope=scope.qdrant_filter())
    allowed_builds = set(scope.build_ids)
    allowed_papers = set(scope.paper_ids)
    evidence: list[EvidenceChunk] = []
    for point in response.points:
        payload = point.payload or {}
        build_id = payload.get("build_id")
        paper_id = payload.get("paper_id")
        inferred_build, inferred_paper = scope.identity_for_point(str(point.id))
        build_id = str(build_id or inferred_build or "")
        paper_id = str(paper_id or inferred_paper or "")
        if build_id not in allowed_builds or not paper_id:
            raise EvidenceScopeError(f"Qdrant point {point.id} has invalid build/paper identity")
        if allowed_papers and paper_id not in allowed_papers:
            raise EvidenceScopeError(f"Qdrant point {point.id} is outside the paper scope")
        if not isinstance(payload.get("text"), str):
            raise EvidenceScopeError(f"Qdrant point {point.id} has no evidence text")
        authors = payload.get("authors") or []
        if isinstance(authors, str):
            authors = [part.strip() for part in authors.split(",") if part.strip()]
        evidence.append(EvidenceChunk(
            id=str(point.id), text=payload["text"], collection=scope.collection,
            build_id=build_id, paper_id=paper_id,
            title=payload.get("file_title") or payload.get("title"),
            arxiv_id=payload.get("arxiv_id"), paper_version=_optional_int(payload.get("paper_version")),
            source_url=payload.get("source_url"), authors=authors,
            year=_optional_int(payload.get("year")),
            page=_optional_int(payload.get("page_number", payload.get("page"))),
            section_header=payload.get("section_header"),
            content_kind=payload.get("content_kind"),
            chunk_index=_optional_int(payload.get("chunk_index")),
            score=getattr(point, "score", None), type=payload.get("type", "text"),
            image_path=payload.get("image_path"), caption=payload.get("caption"),
        ))
    update_span(input={"query": query}, output={"point_ids": [row.id for row in evidence]},
                metadata={"mode": mode, "collection": scope.collection,
                          "scope_kind": scope.kind, "result_count": len(evidence)})
    return evidence
