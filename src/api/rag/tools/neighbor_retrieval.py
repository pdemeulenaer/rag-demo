"""Expand around a textual chunk using its stable within-build ordinal."""
from __future__ import annotations

from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue, Range

from src.api.observability.tracing import observe, update_span
from src.api.rag.contracts import EvidenceChunk, RetrievalScope
from src.api.rag.tools.evidence import (
    EvidenceScopeError,
    evidence_from_point,
    validate_target,
)


MAX_NEIGHBORS_PER_SIDE = 5


@observe(name="get_neighbors", as_type="retriever", capture_input=False, capture_output=False)
def get_neighbors(client, scope: RetrievalScope, *, build_id: str, paper_id: str,
                  chunk_index: int, before: int = 1, after: int = 1) -> list[EvidenceChunk]:
    """Return the anchor and its bounded textual neighbours in document order."""
    if not isinstance(chunk_index, int) or isinstance(chunk_index, bool) or chunk_index < 0:
        raise ValueError("Chunk index must be a non-negative integer")
    if (not isinstance(before, int) or not isinstance(after, int)
            or isinstance(before, bool) or isinstance(after, bool)
            or not 0 <= before <= MAX_NEIGHBORS_PER_SIDE
            or not 0 <= after <= MAX_NEIGHBORS_PER_SIDE):
        raise ValueError(f"Neighbour bounds must be between 0 and {MAX_NEIGHBORS_PER_SIDE}")
    validate_target(scope, build_id, paper_id)
    lower, upper = max(0, chunk_index - before), chunk_index + after
    query_filter = Filter(must=[
        scope.qdrant_filter(),
        FieldCondition(key="build_id", match=MatchValue(value=build_id)),
        FieldCondition(key="paper_id", match=MatchValue(value=paper_id)),
        FieldCondition(key="type", match=MatchAny(any=["text", "chunk"])),
        FieldCondition(key="chunk_index", range=Range(gte=lower, lte=upper)),
    ])
    points, _ = client.scroll(
        collection_name=scope.collection, scroll_filter=query_filter,
        order_by="chunk_index", limit=before + after + 1,
        with_payload=True, with_vectors=False,
    )
    evidence = [evidence_from_point(
        point, scope, expected_build_id=build_id, expected_paper_id=paper_id,
        require_chunk_index=True,
    ) for point in points]
    if any(row.type not in {"text", "chunk"} or not lower <= row.chunk_index <= upper
           for row in evidence):
        raise EvidenceScopeError("Qdrant returned evidence outside the requested neighbour window")
    update_span(input={"build_id": build_id, "paper_id": paper_id,
                       "chunk_index": chunk_index, "before": before, "after": after},
                output={"point_ids": [row.id for row in evidence]},
                metadata={"scope_kind": scope.kind, "result_count": len(evidence),
                          "lower_chunk_index": lower, "upper_chunk_index": upper})
    return evidence
