from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.api.rag.contracts import RetrievalScope, ScopedBuild
from src.api.rag.dispatcher import retrieve_for_mode
from src.api.rag.tools import chunk_search
from src.api.rag.tools.paper_search import search_papers


def catalogue_rows():
    return [
        {"id": "active-build", "paper_id": "paper-1", "source": "arxiv",
         "source_id": "2609.00001", "active_build": "active-build", "deleted": 0,
         "collection": "papers", "version": 2, "status": "ready",
         "metadata": {"title": "Globular cluster dynamics", "authors": ["Ada Star"],
                      "published": "2026-09-01", "abstract": "Tidal evolution and mass loss."}},
        {"id": "retained-build", "paper_id": "paper-1", "source": "arxiv",
         "source_id": "2609.00001", "active_build": "active-build", "deleted": 0,
         "collection": "papers", "version": 1, "status": "ready",
         "metadata": {"title": "Globular cluster dynamics", "authors": ["Ada Star"],
                      "published": "2025-09-01", "abstract": "Earlier tidal evolution."}},
        {"id": "failed-build", "paper_id": "paper-2", "source": "arxiv",
         "source_id": "2609.00002", "active_build": None, "deleted": 0,
         "collection": "papers", "version": 1, "status": "failed",
         "metadata": {"title": "Open clusters", "authors": ["Other"], "year": 2026}},
    ]


def test_retrieval_scope_is_explicit_and_builds_qdrant_filter():
    with pytest.raises(ValueError, match="at least one build"):
        RetrievalScope(collection="papers", build_ids=())
    scope = RetrievalScope(collection="papers", build_ids=("b1", "b1", "b2"),
                           paper_ids=("p1",))
    assert scope.build_ids == ("b1", "b2")
    result = scope.qdrant_filter()
    assert result.must[0].must[0].match.any == ["b1", "b2"]
    assert result.must[1].match.any == ["p1"]


def test_paper_search_distinguishes_active_and_frozen_builds():
    catalogue = SimpleNamespace(all_builds=lambda: catalogue_rows())
    active = RetrievalScope("papers", ("active-build", "retained-build"), kind="active")
    result = search_papers(catalogue, active, author="star", year=2026,
                           terms=["tidal", "mass"], source="arxiv")
    assert [row.build_id for row in result] == ["active-build"]

    frozen = RetrievalScope("papers", ("retained-build",), kind="frozen")
    result = search_papers(catalogue, frozen, title="globular")
    assert [row.build_id for row in result] == ["retained-build"]
    assert result[0].year == 2025


def test_chunk_search_returns_complete_provenance(monkeypatch):
    point = SimpleNamespace(id="point-1", score=0.75, payload={
        "build_id": "build-1", "paper_id": "paper-1", "text": "Evidence",
        "file_title": "Paper", "authors": ["Author"], "year": "2026",
        "paper_version": 2, "page_number": "4", "section_header": "Results",
        "content_kind": "text", "type": "text",
    })
    search = Mock(return_value=SimpleNamespace(points=[point]))
    monkeypatch.setattr(chunk_search, "search_points", search)
    scope = RetrievalScope("papers", ("build-1",), paper_ids=("paper-1",))

    result = chunk_search.search_chunks(Mock(), scope, query="clusters", vector=[1.0],
                                        limit=5, mode="vanilla")

    assert result[0].build_id == "build-1"
    assert result[0].collection == "papers"
    assert result[0].page == 4
    assert result[0].section_header == "Results"
    assert search.call_args.args[1] == "papers"
    assert search.call_args.kwargs["scope"].must[0].must[0].match.any == ["build-1"]


def test_chunk_search_recovers_legacy_identity_and_rejects_drift(monkeypatch):
    scope = RetrievalScope("uploads", ("legacy-build",), builds=(
        ScopedBuild("legacy-build", "legacy-paper", ("legacy-point",)),
    ))
    legacy = SimpleNamespace(id="legacy-point", score=1.0,
                             payload={"text": "Legacy evidence"})
    monkeypatch.setattr(chunk_search, "search_points",
                        Mock(return_value=SimpleNamespace(points=[legacy])))
    assert chunk_search.search_chunks(Mock(), scope, query="legacy", vector=[1.0],
                                      limit=1, mode="vanilla")[0].paper_id == "legacy-paper"

    drift = SimpleNamespace(id="bad", score=1.0, payload={
        "build_id": "outside", "paper_id": "paper", "text": "Wrong corpus"})
    monkeypatch.setattr(chunk_search, "search_points",
                        Mock(return_value=SimpleNamespace(points=[drift])))
    with pytest.raises(chunk_search.EvidenceScopeError, match="invalid build/paper"):
        chunk_search.search_chunks(Mock(), scope, query="legacy", vector=[1.0],
                                   limit=1, mode="vanilla")


def test_dispatcher_keeps_mode_pipelines_separate():
    retrieve = Mock(return_value=[{"id": "candidate", "text": "Evidence"}])
    rerank = Mock(return_value=[{"id": "candidate", "text": "Evidence"}])
    scope = RetrievalScope("papers", ("build",))

    retrieve_for_mode("vanilla", "q", Mock(), top_k=5, collection="papers",
                      scope=scope, retrieve_context=retrieve, rerank_context=rerank)
    assert retrieve.call_args.kwargs["mode"] == "vanilla"
    assert retrieve.call_args.kwargs["top_k"] == 5
    rerank.assert_not_called()

    retrieve_for_mode("hybrid", "q", Mock(), top_k=5, collection="papers",
                      scope=scope, retrieve_context=retrieve, rerank_context=rerank)
    assert retrieve.call_args.kwargs["mode"] == "hybrid"
    assert retrieve.call_args.kwargs["top_k"] == 20
    rerank.assert_called_once_with("q", retrieve.return_value, top_n=5)
