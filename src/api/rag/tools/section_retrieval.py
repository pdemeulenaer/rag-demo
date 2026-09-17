"""Retrieve ordered textual evidence from one exact Markdown section."""
from __future__ import annotations

from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

from src.api.observability.tracing import observe, update_span
from src.api.rag.contracts import EvidenceChunk, RetrievalScope
from src.api.rag.tools.evidence import (
    EvidenceScopeError,
    evidence_from_point,
    validate_target,
)


MAX_SECTION_CHUNKS = 50


@observe(name="get_section", as_type="retriever", capture_input=False, capture_output=False)
def get_section(client, scope: RetrievalScope, *, build_id: str, paper_id: str,
                section_header: str, limit: int = 12) -> list[EvidenceChunk]:
    """Return the first ordered chunks whose section breadcrumb exactly matches."""
    section_header = section_header.strip()
    if not section_header:
        raise ValueError("Section header must not be empty")
    if not 1 <= limit <= MAX_SECTION_CHUNKS:
        raise ValueError(f"Section limit must be between 1 and {MAX_SECTION_CHUNKS}")
    validate_target(scope, build_id, paper_id)
    query_filter = Filter(must=[
        scope.qdrant_filter(),
        FieldCondition(key="build_id", match=MatchValue(value=build_id)),
        FieldCondition(key="paper_id", match=MatchValue(value=paper_id)),
        FieldCondition(key="type", match=MatchAny(any=["text", "chunk"])),
        FieldCondition(key="section_header", match=MatchValue(value=section_header)),
    ])
    points, _ = client.scroll(
        collection_name=scope.collection, scroll_filter=query_filter,
        order_by="chunk_index", limit=limit, with_payload=True, with_vectors=False,
    )
    evidence = [evidence_from_point(
        point, scope, expected_build_id=build_id, expected_paper_id=paper_id,
        require_chunk_index=True,
    ) for point in points]
    if any(row.section_header != section_header or row.type not in {"text", "chunk"}
           for row in evidence):
        raise EvidenceScopeError("Qdrant returned evidence outside the requested section")
    update_span(input={"build_id": build_id, "paper_id": paper_id,
                       "section_header": section_header, "limit": limit},
                output={"point_ids": [row.id for row in evidence]},
                metadata={"scope_kind": scope.kind, "result_count": len(evidence)})
    return evidence
