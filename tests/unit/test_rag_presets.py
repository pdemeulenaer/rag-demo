import asyncio
import importlib
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, Request, Response

from src.api.api.models import RAGRequest


@pytest.fixture
def runtime(monkeypatch):
    # Imports in the legacy app create provider clients; never read/use real keys.
    for key in ["OPENAI_API_KEY", "GROQ_API_KEY", "COHERE_API_KEY", "LANGSMITH_API_KEY"]:
        monkeypatch.setenv(key, "offline-test")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("QDRANT_PORT", "6333")
    monkeypatch.setenv("QDRANT_API_KEY", "")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setenv("STORAGE_MODE", "LOCAL")
    monkeypatch.setenv("EVALUATION_MODE", "true")
    # Prevent the legacy metadata client's import-time server-version request.
    with patch("qdrant_client.QdrantClient", Mock()), patch("langsmith.Client", Mock()):
        retrieval = importlib.import_module("src.api.rag.retrieval")
        router = importlib.import_module("src.api.api.rag_router")
    return retrieval, router


@pytest.mark.parametrize("mode,rerank_calls", [("vanilla", 0), ("hybrid", 1)])
def test_pipeline_modes_and_citation_filter_order(runtime, monkeypatch, mode, rerank_calls):
    retrieval, _ = runtime
    contexts = [
        {"id": "uncited", "title": "Paper A", "authors": ["Author"], "year": 2026, "page": 1, "text": "First"},
        {"id": "cited", "title": "Paper A", "authors": ["Author"], "year": 2026, "page": 2, "text": "Second"},
    ]
    retrieve = Mock(return_value=contexts)
    rerank = Mock(return_value=contexts)
    monkeypatch.setattr(retrieval, "retrieve_context", retrieve)
    monkeypatch.setattr(retrieval, "rerank_context", rerank)
    monkeypatch.setattr(retrieval, "build_prompt", Mock(return_value=[]))
    monkeypatch.setattr(retrieval, "generate_answer", Mock(return_value=SimpleNamespace(
        answer="Grounded", retrieved_context_ids=["cited"])))
    result = retrieval.rag_pipeline("question", Mock(), "session", mode=mode, collection="papers", scope="ready")
    assert rerank.call_count == rerank_calls  # Explicit mode overrides legacy EVALUATION_MODE.
    assert retrieve.call_args.kwargs["collection"] == "papers"
    assert retrieve.call_args.kwargs["scope"] == "ready"
    assert len(result["sources"]) == 1
    assert result["sources"][0].id == "cited"
    assert result["sources"][0].page == [2]


def test_empty_evidence_does_not_generate(runtime, monkeypatch):
    retrieval, _ = runtime
    monkeypatch.setattr(retrieval, "retrieve_context", Mock(return_value=[]))
    generate = Mock()
    monkeypatch.setattr(retrieval, "generate_answer", generate)
    result = retrieval.rag_pipeline("question", Mock(), "session", mode="vanilla")
    assert result["sources"] == []
    generate.assert_not_called()


def request():
    return Request({"type": "http", "headers": [(b"cookie", b"session_id=test-session")],
                    "state": {"request_id": "request-1"}})


@pytest.mark.parametrize("mode", ["vanilla", "hybrid"])
def test_router_presets_bypass_intent(runtime, monkeypatch, mode):
    _, router = runtime
    import src.api.api.papers_router as papers_router

    async def inline(fn, *args, **kwargs):
        return fn(*args, **kwargs)
    monkeypatch.setattr("starlette.concurrency.run_in_threadpool", inline)
    classify = Mock(side_effect=AssertionError("Explicit preset must bypass classifier"))
    monkeypatch.setattr(router, "classify_question", classify)
    pipeline = Mock(return_value={"answer": "Evidence", "sources": [], "images": []})
    monkeypatch.setattr(router, "rag_pipeline_wrapper", pipeline)
    monkeypatch.setattr(router, "add_message", Mock())
    monkeypatch.setattr(router, "get_memory", Mock(return_value=SimpleNamespace(summary="", recent_messages=[])))
    monkeypatch.setattr(router, "_process_images", Mock(return_value=[]))
    monkeypatch.setattr(papers_router, "active_corpus", lambda: (
        SimpleNamespace(PAPERS_COLLECTION="papers"), [{"id": "ready-1"}], "snapshot-1"))
    result = asyncio.run(router.rag(request(), RAGRequest(query="Compare papers", mode=mode, corpus="arxiv"), Response()))
    assert result.mode == mode
    assert result.corpus_snapshot == "snapshot-1"
    assert f":arxiv:{mode}:" in pipeline.call_args.args[1]
    assert pipeline.call_args.kwargs["scope"].should[0].must[0].match.value == "ready-1"
    classify.assert_not_called()


def test_corpus_change_rejected_before_model_call(runtime, monkeypatch):
    _, router = runtime
    import src.api.api.papers_router as papers_router

    async def inline(fn, *args, **kwargs):
        return fn(*args, **kwargs)
    monkeypatch.setattr("starlette.concurrency.run_in_threadpool", inline)
    monkeypatch.setattr(papers_router, "active_corpus", lambda: (
        SimpleNamespace(PAPERS_COLLECTION="papers"), [{"id": "new"}], "new-snapshot"))
    pipeline = Mock()
    monkeypatch.setattr(router, "rag_pipeline_wrapper", pipeline)
    with pytest.raises(HTTPException) as error:
        asyncio.run(router.rag(request(), RAGRequest(query="Question", mode="vanilla", corpus="arxiv",
                                                     corpus_snapshot="old-snapshot"), Response()))
    assert error.value.status_code == 409
    pipeline.assert_not_called()


def test_request_defaults_preserve_legacy_contract():
    payload = RAGRequest(query="Question")
    assert payload.mode is None
    assert payload.corpus == "uploads"
    with pytest.raises(ValueError):
        RAGRequest(query="Question", mode="graph")
