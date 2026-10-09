"""Shared scope and payload validation for read-only evidence tools."""
from __future__ import annotations

from src.api.rag.contracts import EvidenceChunk, RetrievalScope


class EvidenceScopeError(ValueError):
    """A tool request or returned point escaped its explicit corpus identity."""


def optional_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def validate_target(scope: RetrievalScope, build_id: str, paper_id: str) -> None:
    """Fail before querying when a requested paper/build pair is outside scope."""
    if build_id not in scope.build_ids:
        raise EvidenceScopeError(f"Build {build_id} is outside the retrieval scope")
    if scope.paper_ids and paper_id not in scope.paper_ids:
        raise EvidenceScopeError(f"Paper {paper_id} is outside the retrieval scope")
    registered = next((build for build in scope.builds if build.build_id == build_id), None)
    if registered and registered.paper_id and registered.paper_id != paper_id:
        raise EvidenceScopeError("Paper/build identity does not match the retrieval scope")


def evidence_from_point(point, scope: RetrievalScope, *, expected_build_id: str | None = None,
                        expected_paper_id: str | None = None,
                        require_chunk_index: bool = False) -> EvidenceChunk:
    """Convert a Qdrant point only after validating complete evidence identity."""
    payload = point.payload or {}
    build_id = payload.get("build_id")
    paper_id = payload.get("paper_id")
    inferred_build, inferred_paper = scope.identity_for_point(str(point.id))
    build_id = str(build_id or inferred_build or "")
    paper_id = str(paper_id or inferred_paper or "")
    if build_id not in set(scope.build_ids) or not paper_id:
        raise EvidenceScopeError(f"Qdrant point {point.id} has invalid build/paper identity")
    if scope.paper_ids and paper_id not in set(scope.paper_ids):
        raise EvidenceScopeError(f"Qdrant point {point.id} is outside the paper scope")
    if expected_build_id and build_id != expected_build_id:
        raise EvidenceScopeError(f"Qdrant point {point.id} is outside the requested build")
    if expected_paper_id and paper_id != expected_paper_id:
        raise EvidenceScopeError(f"Qdrant point {point.id} is outside the requested paper")
    if not isinstance(payload.get("text"), str):
        raise EvidenceScopeError(f"Qdrant point {point.id} has no evidence text")
    chunk_index = optional_int(payload.get("chunk_index"))
    if require_chunk_index and chunk_index is None:
        raise EvidenceScopeError(f"Qdrant point {point.id} has no stable chunk index")
    authors = payload.get("authors") or []
    if isinstance(authors, str):
        authors = [part.strip() for part in authors.split(",") if part.strip()]
    return EvidenceChunk(
        id=str(point.id), text=payload["text"], collection=scope.collection,
        build_id=build_id, paper_id=paper_id,
        title=payload.get("file_title") or payload.get("title"),
        arxiv_id=payload.get("arxiv_id"),
        paper_version=optional_int(payload.get("paper_version")),
        source_url=payload.get("source_url"), authors=authors,
        year=optional_int(payload.get("year")),
        page=optional_int(payload.get("page_number", payload.get("page"))),
        section_header=payload.get("section_header"),
        content_kind=payload.get("content_kind"), chunk_index=chunk_index,
        score=getattr(point, "score", None), type=payload.get("type", "text"),
        image_path=payload.get("image_path"), caption=payload.get("caption"),
    )
