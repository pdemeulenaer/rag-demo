"""Search authoritative paper/build metadata in PostgreSQL."""
from __future__ import annotations

from collections.abc import Iterable

from src.api.observability.tracing import observe, update_span
from src.api.rag.contracts import PaperMatch, RetrievalScope


def _authors(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(author) for author in value]
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def _year(value: object) -> int | None:
    try:
        return int(str(value)[:4]) if value is not None else None
    except (TypeError, ValueError):
        return None


@observe(name="search_papers", as_type="retriever", capture_input=False, capture_output=False)
def search_papers(catalogue, scope: RetrievalScope, *, title: str | None = None,
                  author: str | None = None, year: int | None = None,
                  terms: Iterable[str] = (), source: str | None = None,
                  limit: int = 10) -> list[PaperMatch]:
    """Resolve ready catalogue builds without escaping the supplied corpus scope.

    Active scopes accept only each paper's current active build. Frozen scopes
    intentionally permit retained ready builds named by an evaluation snapshot.
    All supplied metadata filters are combined with AND semantics.
    """
    if limit < 1:
        raise ValueError("Paper search limit must be positive")
    wanted_builds = set(scope.build_ids)
    wanted_terms = [str(term).strip().casefold() for term in terms if str(term).strip()]
    title_query = title.strip().casefold() if title else None
    author_query = author.strip().casefold() if author else None
    matches: list[PaperMatch] = []
    if hasattr(catalogue, "scoped_ready_builds"):
        rows = catalogue.scoped_ready_builds(
            scope.collection, scope.build_ids, active_only=scope.kind == "active"
        )
    else:  # Lightweight protocol-compatible catalogue doubles used by callers/tests.
        rows = catalogue.all_builds()
    for row in rows:
        if str(row["id"]) not in wanted_builds or row["collection"] != scope.collection:
            continue
        if row["status"] != "ready":
            continue
        if scope.kind == "active" and row.get("deleted"):
            continue
        if scope.kind == "active" and row["id"] != row.get("active_build"):
            continue
        if source and row.get("source") != source:
            continue
        metadata = dict(row.get("metadata") or {})
        row_title = str(metadata.get("title") or metadata.get("file_name") or "Untitled")
        row_authors = _authors(metadata.get("authors"))
        row_year = _year(metadata.get("year") or metadata.get("published"))
        searchable = " ".join((row_title, str(metadata.get("abstract") or ""))).casefold()
        if title_query and title_query not in row_title.casefold():
            continue
        if author_query and not any(author_query in value.casefold() for value in row_authors):
            continue
        if year is not None and row_year != year:
            continue
        if wanted_terms and not all(term in searchable for term in wanted_terms):
            continue
        matches.append(PaperMatch(
            paper_id=str(row["paper_id"]), build_id=str(row["id"]),
            source=str(row["source"]), source_id=str(row["source_id"]),
            collection=str(row["collection"]), version=int(row["version"]),
            title=row_title, authors=row_authors, year=row_year,
            abstract=metadata.get("abstract"), metadata=metadata,
        ))
    matches.sort(key=lambda item: (item.title.casefold(), item.build_id))
    result = matches[:limit]
    update_span(input={"title": title, "author": author, "year": year,
                       "terms": wanted_terms, "source": source},
                output={"build_ids": [row.build_id for row in result]},
                metadata={"scope_kind": scope.kind, "result_count": len(result)})
    return result
