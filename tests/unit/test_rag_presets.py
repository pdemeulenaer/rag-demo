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
    for key in ["OPENAI_API_KEY", "GROQ_API_KEY", "COHERE_API_KEY"]:
        monkeypatch.setenv(key, "offline-test")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("QDRANT_PORT", "6333")
    monkeypatch.setenv("QDRANT_API_KEY", "")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setenv("STORAGE_MODE", "LOCAL")
    monkeypatch.setenv("EVALUATION_MODE", "true")
    # Prevent the legacy metadata client's import-time server-version request.
    with patch("qdrant_client.QdrantClient", Mock()):
        retrieval = importlib.import_module("src.api.rag.retrieval")
        router = importlib.import_module("src.api.api.rag_router")
    return retrieval, router


@pytest.mark.parametrize("mode,rerank_calls", [
    ("vanilla", 0), ("hybrid", 0), ("hybrid_rerank", 1),
])
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


def test_federated_retrieval_searches_and_merges_collections(runtime, monkeypatch):
    retrieval, _ = runtime
    from src.api.rag.contracts import (
        EvidenceChunk,
        FederatedRetrievalScope,
        RetrievalScope,
    )

    scope = FederatedRetrievalScope((
        RetrievalScope("arxiv", ("arxiv-build",)),
        RetrievalScope("uploads", ("upload-build",)),
    ))

    def search(_client, child, **_kwargs):
        score = 0.7 if child.collection == "arxiv" else 0.9
        return [EvidenceChunk(
            id=f"{child.collection}-point", text=child.collection,
            collection=child.collection, build_id=child.build_ids[0],
            paper_id=f"{child.collection}-paper", score=score,
        )]

    chunk_search = Mock(side_effect=search)
    monkeypatch.setattr(retrieval, "search_chunks", chunk_search)
    monkeypatch.setattr(retrieval, "get_embedding", Mock(return_value=[1.0, 0.0]))

    rows = retrieval.retrieve_context(
        "question", Mock(), top_k=2, mode="hybrid", scope=scope,
    )

    assert [row["collection"] for row in rows] == ["uploads", "arxiv"]
    assert chunk_search.call_count == 2


def test_openai_generation_uses_model_schema_and_retries_invalid_citations(runtime, monkeypatch):
    retrieval, _ = runtime
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=2, total_tokens=12)
    invalid = SimpleNamespace(usage=usage, choices=[SimpleNamespace(message=SimpleNamespace(
        content='{"answer":"Unsupported","retrieved_context_ids":["unknown"]}'))])
    valid = SimpleNamespace(usage=usage, choices=[SimpleNamespace(message=SimpleNamespace(
        content='{"answer":"Grounded","retrieved_context_ids":["allowed"]}'))])
    create = Mock(side_effect=[invalid, valid])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(retrieval, "openai_client", Mock(return_value=client))

    response = retrieval.generate_answer([], "gpt-4.1-nano", {"allowed"})

    assert response.answer == "Grounded"
    assert create.call_count == 2
    schema = create.call_args.kwargs["response_format"]["json_schema"]
    assert schema["strict"] is True
    assert schema["schema"] == retrieval.RAGGenerationResponse.model_json_schema()
    assert "used_chunks_rationale" not in schema["schema"]["properties"]


def request():
    return Request({"type": "http", "headers": [(b"cookie", b"session_id=test-session")],
                    "state": {"request_id": "request-1"}})


@pytest.mark.parametrize("mode", ["vanilla", "hybrid", "hybrid_rerank", "agentic"])
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
    assert pipeline.call_args.kwargs["scope"].build_ids == ("ready-1",)
    assert pipeline.call_args.kwargs["scope"].collection == "papers"
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


def test_all_corpus_builds_a_federated_scope(runtime, monkeypatch):
    _, router = runtime
    import src.api.api.papers_router as papers_router
    from src.api.rag.contracts import FederatedRetrievalScope

    async def inline(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def active(source="arxiv"):
        if source == "uploads":
            return SimpleNamespace(PAPERS_COLLECTION="arxiv-papers"), [
                {"id": "upload-build", "paper_id": "upload-paper", "manifest": {}}
            ], "uploads-snapshot"
        return SimpleNamespace(PAPERS_COLLECTION="arxiv-papers"), [
            {"id": "arxiv-build", "paper_id": "arxiv-paper", "manifest": {}}
        ], "arxiv-snapshot"

    monkeypatch.setattr("starlette.concurrency.run_in_threadpool", inline)
    monkeypatch.setattr(papers_router, "active_corpus", active)
    pipeline = Mock(return_value={"answer": "Evidence", "sources": [], "images": []})
    monkeypatch.setattr(router, "rag_pipeline_wrapper", pipeline)
    monkeypatch.setattr(router, "add_message", Mock())
    monkeypatch.setattr(router, "get_memory", Mock(return_value=SimpleNamespace(
        summary="", recent_messages=[])))
    monkeypatch.setattr(router, "_process_images", Mock(return_value=[]))

    result = asyncio.run(router.rag(
        request(), RAGRequest(query="Compare sources", mode="hybrid", corpus="all"),
        Response(),
    ))

    scope = pipeline.call_args.kwargs["scope"]
    assert isinstance(scope, FederatedRetrievalScope)
    assert scope.collections == ("arxiv-papers", "uploaded_papers_v2")
    assert set(scope.build_ids) == {"arxiv-build", "upload-build"}
    assert result.corpus_snapshot
    assert f":all:hybrid:" in pipeline.call_args.args[1]


def test_request_defaults_preserve_legacy_contract():
    payload = RAGRequest(query="Question")
    assert payload.mode is None
    assert payload.corpus == "uploads"
    with pytest.raises(ValueError):
        RAGRequest(query="Question", mode="graph")


def test_agentic_abstention_skips_answer_generation(runtime, monkeypatch):
    retrieval, _ = runtime
    from src.api.rag.contracts import EvidenceChunk, RetrievalScope
    from src.api.rag.modes.agentic.contracts import AgentExecutionMetadata
    from src.api.rag.modes.agentic.executor import AgentRunResult
    import src.api.rag.modes.agentic.executor as agent_executor

    execution = AgentExecutionMetadata(
        question_scope="direct",
        plan_summary="Search for direct supporting evidence.",
        stop_reason="insufficient_evidence",
        rounds=1,
        tool_calls=1,
        evidence_count=1,
        planner_tokens=20,
        elapsed_seconds=0.1,
        actions=[],
    )
    evidence = EvidenceChunk(
        id="partial", text="Partial evidence", collection="papers",
        build_id="build", paper_id="paper",
    )
    monkeypatch.setattr(
        agent_executor,
        "run_agentic",
        Mock(return_value=AgentRunResult([evidence], execution, False)),
    )
    generate = Mock()
    monkeypatch.setattr(retrieval, "generate_answer", generate)

    result = retrieval.rag_pipeline(
        "question", Mock(), "session", mode="agentic", collection="papers",
        scope=RetrievalScope("papers", ("build",)), catalogue=Mock(), agent_model=Mock(),
    )

    assert "could not find sufficient indexed evidence" in result["answer"]
    assert result["execution"].stop_reason.value == "insufficient_evidence"
    assert result["sources"] == []
    generate.assert_not_called()


def test_successful_agentic_execution_reaches_shared_generator_and_trace(runtime, monkeypatch):
    retrieval, _ = runtime
    from src.api.rag.contracts import EvidenceChunk, RetrievalScope
    from src.api.rag.modes.agentic.contracts import AgentExecutionMetadata
    from src.api.rag.modes.agentic.executor import AgentRunResult
    import src.api.rag.modes.agentic.executor as agent_executor

    execution = AgentExecutionMetadata(
        question_scope="direct", plan_summary="Retrieve one direct result.",
        stop_reason="sufficient", rounds=1, tool_calls=1, evidence_count=1,
        planner_tokens=25, elapsed_seconds=0.2, actions=[],
    )
    evidence = EvidenceChunk(
        id="point", text="Direct result", collection="papers",
        build_id="build", paper_id="paper", title="Paper", page=2,
    )
    monkeypatch.setattr(
        agent_executor, "run_agentic",
        Mock(return_value=AgentRunResult([evidence], execution, True)),
    )
    monkeypatch.setattr(retrieval, "build_prompt", Mock(return_value=[]))
    monkeypatch.setattr(retrieval, "generate_answer", Mock(return_value=SimpleNamespace(
        answer="Grounded", retrieved_context_ids=["point"])))
    update = Mock()
    monkeypatch.setattr(retrieval, "update_span", update)

    result = retrieval.rag_pipeline(
        "question", Mock(), "session", mode="agentic", collection="papers",
        scope=RetrievalScope("papers", ("build",)), catalogue=Mock(), agent_model=Mock(),
    )

    assert result["answer"] == "Grounded"
    assert result["sources"][0].id == "point"
    assert result["execution"].stop_reason.value == "sufficient"
    trace_outputs = [call.kwargs.get("output", {}) for call in update.call_args_list]
    assert any(output.get("agent_execution", {}).get("stop_reason") == "sufficient"
               for output in trace_outputs)


def test_agentic_generation_failure_retains_safe_execution_metadata(runtime, monkeypatch):
    retrieval, _ = runtime
    from src.api.rag.contracts import EvidenceChunk, RetrievalScope
    from src.api.rag.modes.agentic.contracts import AgentExecutionMetadata
    from src.api.rag.modes.agentic.executor import AgentRunResult
    import src.api.rag.modes.agentic.executor as agent_executor

    execution = AgentExecutionMetadata(
        question_scope="direct", plan_summary="Use collected evidence.",
        stop_reason="insufficient_evidence", synthesis_policy="evidence_fallback",
        rounds=1, tool_calls=1, evidence_count=1, planner_tokens=25,
        elapsed_seconds=0.2, actions=[],
    )
    evidence = EvidenceChunk(
        id="point", text="Direct result", collection="papers",
        build_id="build", paper_id="paper", title="Paper", page=2,
    )
    monkeypatch.setattr(
        agent_executor, "run_agentic",
        Mock(return_value=AgentRunResult([evidence], execution, True)),
    )
    monkeypatch.setattr(retrieval, "build_prompt", Mock(return_value=[]))
    monkeypatch.setattr(
        retrieval, "generate_answer", Mock(side_effect=ValueError("invalid citations")),
    )

    with pytest.raises(ValueError) as caught:
        retrieval.rag_pipeline(
            "question", Mock(), "session", mode="agentic", collection="papers",
            scope=RetrievalScope("papers", ("build",)), catalogue=Mock(), agent_model=Mock(),
        )

    assert caught.value.agent_execution.synthesis_policy == "evidence_fallback"
