import asyncio
import importlib
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, Request, Response

from src.api.api.models import RAGRequest


def native_chat_client(parse):
    client = Mock()
    client.with_options.return_value = client
    client.chat.completions.parse = parse
    return client


def parsed_completion(raw, schema):
    raw.choices[0].message.parsed = schema.model_validate_json(raw.choices[0].message.content)
    return raw


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
    claim = retrieval.RAGClaim(text="Grounded", cited_context_ids=["cited"], need_ids=[])
    response = retrieval.RAGGenerationResponse(claims=[claim])
    monkeypatch.setattr(retrieval, "generate_answer", Mock(return_value=response))
    timings = {}
    result = retrieval.rag_pipeline(
        "question", Mock(), "session", mode=mode, collection="papers", scope="ready",
        stage_timings=timings,
    )
    assert timings["retrieval_seconds"] >= 0
    assert timings["generation_seconds"] >= 0
    assert ("rerank_seconds" in timings) == (mode == "hybrid_rerank")
    assert rerank.call_count == rerank_calls  # Explicit mode overrides legacy EVALUATION_MODE.
    assert retrieve.call_args.kwargs["collection"] == "papers"
    assert retrieve.call_args.kwargs["scope"] == "ready"
    assert len(result["sources"]) == 1
    assert result["sources"][0].id == "cited"
    assert result["sources"][0].page == [2]


def test_reranker_persists_full_candidate_order_and_paper_diversity(runtime, monkeypatch):
    retrieval, _ = runtime
    candidates = [
        {"id": "one", "paper_id": "paper-a", "title": "Paper A", "text": "A"},
        {"id": "two", "paper_id": "paper-b", "title": "Paper B", "text": "B"},
        {"id": "three", "paper_id": "paper-a", "title": "Paper A", "text": "C"},
    ]
    rerank = Mock(return_value=SimpleNamespace(results=[
        SimpleNamespace(index=2, relevance_score=0.9),
        SimpleNamespace(index=0, relevance_score=0.8),
        SimpleNamespace(index=1, relevance_score=0.7),
    ]))
    monkeypatch.setattr(retrieval, "cohere_client", SimpleNamespace(rerank=rerank))

    result = retrieval.rerank_context("compare", candidates, top_n=2)

    assert [row["id"] for row in result] == ["three", "one"]
    assert rerank.call_args.kwargs["top_n"] == 3
    assert result.diagnostics["candidate_paper_count"] == 2
    assert result.diagnostics["selected_paper_count"] == 1
    assert [row["id"] for row in result.diagnostics["ranked_candidates"]] == [
        "three", "one", "two",
    ]


def test_reranker_reserves_best_chunk_from_each_explicitly_named_paper(runtime, monkeypatch):
    retrieval, _ = runtime
    candidates = [
        {"id": "a-best", "paper_id": "paper-a", "title": "Alpha Cluster Study", "text": "A1"},
        {"id": "a-next", "paper_id": "paper-a", "title": "Alpha Cluster Study", "text": "A2"},
        {"id": "b-best", "paper_id": "paper-b", "title": "Beta Cluster Study", "text": "B1"},
    ]
    rerank = Mock(return_value=SimpleNamespace(results=[
        SimpleNamespace(index=0, relevance_score=0.99),
        SimpleNamespace(index=1, relevance_score=0.98),
        SimpleNamespace(index=2, relevance_score=0.5),
    ]))
    monkeypatch.setattr(retrieval, "cohere_client", SimpleNamespace(rerank=rerank))

    result = retrieval.rerank_context(
        'Compare "Alpha Cluster Study" with "Beta Cluster Study".', candidates, top_n=2,
    )

    assert [row["id"] for row in result] == ["a-best", "b-best"]
    assert result.diagnostics["named_paper_ids"] == ["paper-a", "paper-b"]
    assert result.diagnostics["reserved_candidate_ids"] == ["a-best", "b-best"]
    assert result.diagnostics["named_paper_diversity_guard_applied"] is True


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
        content='{"claims":[{"text":"Unsupported","cited_context_ids":["unknown"],"need_ids":[]}]}'))])
    valid = SimpleNamespace(usage=usage, choices=[SimpleNamespace(message=SimpleNamespace(
        content='{"claims":[{"text":"Grounded","cited_context_ids":["allowed"],"need_ids":[]}]}'))])
    create = Mock(side_effect=[parsed_completion(row, retrieval.RAGGenerationResponse)
                               for row in (invalid, valid)])
    client = native_chat_client(create)
    monkeypatch.setattr(retrieval, "openai_client", Mock(return_value=client))

    response = retrieval.generate_answer([], "gpt-4.1-nano", {"allowed"})

    assert response.answer == "Grounded"
    assert create.call_count == 2
    assert create.call_args.kwargs["response_format"] is retrieval.RAGGenerationResponse
    client.with_options.assert_called_once_with(max_retries=0)


def test_agentic_malformed_openai_json_exposes_safe_finish_diagnostics(runtime, monkeypatch):
    retrieval, _ = runtime
    usage = SimpleNamespace(prompt_tokens=25, completion_tokens=4096, total_tokens=4121)
    choice = SimpleNamespace(
        message=SimpleNamespace(content='{"claims":', refusal=None),
        finish_reason="length",
    )
    raw = SimpleNamespace(usage=usage, choices=[choice])
    client = Mock()
    client.with_options.return_value = client
    from openai import LengthFinishReasonError
    client.chat.completions.parse.side_effect = LengthFinishReasonError(completion=raw)
    monkeypatch.setattr(retrieval, "openai_client", Mock(return_value=client))
    monkeypatch.setattr(retrieval, "is_openai_model", lambda model: True)
    span = Mock()

    class SpanContext:
        def __enter__(self):
            return span

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(retrieval, "observation", lambda **_kwargs: SpanContext())
    with pytest.raises(retrieval.AgenticStructuredOutputError) as caught:
        retrieval._agentic_structured_request(
            [{"role": "user", "content": "private prompt"}],
            retrieval.RAGGenerationResponse, "verify", "gpt-5-mini",
        )

    details = caught.value.safe_diagnostics
    assert details["validation_error_codes"] == ["completion_limit"]
    assert details["provider_finish_reason"] == "length"
    assert details["provider_completion_tokens"] == 4096
    assert details["provider_content_chars"] == len('{"claims":')
    assert details["provider_refusal"] is False
    assert "private prompt" not in str(details)
    span.update.assert_called_once()
    assert span.update.call_args.kwargs["output"]["structured_output_valid"] is False


def test_baseline_structured_failure_uses_only_existing_retry_and_abstains(runtime, monkeypatch):
    from src.api.core.structured import StructuredOutputError

    retrieval, _ = runtime
    parse = Mock(side_effect=StructuredOutputError({"validation_error_codes": ["provider_refusal"]}))
    client = native_chat_client(parse)
    monkeypatch.setattr(retrieval, "openai_client", Mock(return_value=client))
    monkeypatch.setattr(retrieval, "retrieve_context", Mock(return_value=[
        {"id": "a", "title": "Study", "text": "Evidence", "paper_id": "paper-a"},
    ]))
    monkeypatch.setattr(retrieval, "build_prompt", Mock(return_value=[]))

    result = retrieval.rag_pipeline("Question", Mock(), "session", mode="hybrid")

    assert parse.call_count == 2
    assert result["claims"] == []
    assert result["generation_diagnostics"]["status"] == "safe_abstention"
    assert len(result["generation_diagnostics"]["validation_failures"]) == 2
    client.with_options.assert_called_once_with(max_retries=0)


def test_openai_generation_retries_missing_required_paper_citation(runtime, monkeypatch):
    retrieval, _ = runtime
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=2, total_tokens=12)
    incomplete = SimpleNamespace(usage=usage, choices=[SimpleNamespace(message=SimpleNamespace(
        content='{"claims":[{"text":"Only A","cited_context_ids":["a"],"need_ids":[]}]}'))])
    complete = SimpleNamespace(usage=usage, choices=[SimpleNamespace(message=SimpleNamespace(
        content='{"claims":[{"text":"A and B","cited_context_ids":["a","b"],"need_ids":[]}]}'))])
    create = Mock(side_effect=[parsed_completion(row, retrieval.RAGGenerationResponse)
                               for row in (incomplete, complete)])
    client = native_chat_client(create)
    monkeypatch.setattr(retrieval, "openai_client", Mock(return_value=client))

    response = retrieval.generate_answer(
        [{"role": "user", "content": "Compare them"}], "gpt-4.1-nano", {"a", "b"},
        {"Alpha Cluster Study": {"a"}, "Beta Cluster Study": {"b"}},
    )

    assert response.retrieved_context_ids == ["a", "b"]
    assert create.call_count == 2
    repair_message = create.call_args.kwargs["messages"][-1]["content"]
    assert "Alpha Cluster Study" in repair_message
    assert "Beta Cluster Study" in repair_message


def test_baseline_citation_retry_prompt_names_failure_and_paper_mapping(runtime):
    retrieval, _ = runtime
    messages = retrieval._citation_retry_prompt(
        [], {"Cluster Paper": {"chunk-radius"}},
        validation_code="missing_required_source_group",
    )
    repair = messages[-1]["content"]

    assert "missing_required_source_group" in repair
    assert "Cluster Paper" in repair
    assert "chunk-radius" in repair


def test_required_citation_groups_accept_agent_resolved_paper_ids(runtime):
    retrieval, _ = runtime
    contexts = [
        {"id": "a1", "paper_id": "paper-a", "title": "Paper A", "text": "A"},
        {"id": "b1", "paper_id": "paper-b", "title": "Paper B", "text": "B"},
    ]

    groups = retrieval._required_citation_groups(
        "Compare the two resolved papers.", contexts, ("paper-a", "paper-b"),
    )

    assert groups == {"Paper A": {"a1"}, "Paper B": {"b1"}}


def test_baseline_validator_rejects_agentic_need_labels(runtime):
    retrieval, _ = runtime
    response = retrieval.RAGGenerationResponse(claims=[
        retrieval.RAGClaim(text="A", cited_context_ids=["a"], need_ids=["r1"]),
    ])
    with pytest.raises(retrieval.InvalidCitationIdsError, match="unexpected_claim_need_ids"):
        retrieval._validate_context_ids(response, {"a"})




def test_agentic_partial_answer_survives_missing_named_paper_and_exposes_diagnostics(runtime, monkeypatch):
    retrieval, _ = runtime
    from src.api.rag.contracts import EvidenceChunk, RetrievalScope
    from src.api.rag.modes.agentic.contracts import AgentExecutionMetadata, AnswerRequirement
    from src.api.rag.modes.agentic.executor import AgentRunResult
    from src.api.rag.modes.agentic.answering import AnswerReview
    import src.api.rag.modes.agentic.executor as executor

    execution = AgentExecutionMetadata(
        question_scope="cross_paper", plan_summary="Only one paper retrieved.",
        stop_reason="insufficient_evidence", synthesis_policy="evidence_fallback",
        rounds=1, tool_calls=1, evidence_count=1, planner_tokens=20,
        elapsed_seconds=0.2, actions=[],
    )
    evidence = EvidenceChunk(id="a", text="The mass is 2 solar masses.",
        collection="papers", build_id="build-a", paper_id="paper-a", title="Paper A", page=2)
    requirements = [
        AnswerRequirement(id="r1", description="Report the mass in Paper A."),
        AnswerRequirement(id="r2", description="Report the mass in Paper B."),
    ]
    monkeypatch.setattr(executor, "run_agentic", Mock(return_value=AgentRunResult(
        [evidence], execution, True, requirements=requirements)))
    monkeypatch.setattr(retrieval, "_resolve_required_papers", Mock(return_value=[
        SimpleNamespace(build_id="build-a"), SimpleNamespace(build_id="build-b"),
    ]))
    monkeypatch.setattr(retrieval, "build_prompt", Mock(return_value=[]))
    review = AnswerReview(claims=[{"claim_index": 0, "supported": True, "feedback": "",
        "evidence_quotes": [{"context_id": "a", "quote": "The mass is 2 solar masses."}]}],
        requirements=[
            {"requirement_id": "r1", "status": "satisfied", "claim_indices": [0], "feedback": ""},
            {"requirement_id": "r2", "status": "missing", "claim_indices": [],
             "feedback": "No evidence from Paper B."},
        ], unplanned_requests=[])
    request = Mock(side_effect=[
        retrieval.RAGGenerationResponse(claims=[retrieval.RAGClaim(
            text="The mass in Paper A is 2 solar masses.", cited_context_ids=["a"], need_ids=[])]),
        review, retrieval.RAGGenerationResponse(claims=[]), review,
    ])
    monkeypatch.setattr(retrieval, "_agentic_structured_request", request)
    baseline = Mock(side_effect=AssertionError("Agentic must not use baseline hard gates"))
    monkeypatch.setattr(retrieval, "generate_answer", baseline)

    result = retrieval.rag_pipeline("Compare the masses.", Mock(), "session", mode="agentic",
        scope=RetrievalScope("papers", ("build-a", "build-b")), catalogue=Mock(), agent_model=Mock())

    assert "The mass in Paper A is 2 solar masses. [1]" in result["answer"]
    assert "I could not verify" in result["answer"]
    assert "Report the mass in Paper B." in result["answer"]
    assert result["generation_diagnostics"]["status"] == "partial"
    assert result["cited_context_ids"] == ["a"]
    assert result["claims"][0]["need_ids"] == ["r1"]
    assert request.call_count == 4
    baseline.assert_not_called()


def test_agentic_openai_adapter_is_schema_strict_and_has_no_hidden_retries(runtime, monkeypatch):
    retrieval, _ = runtime
    from src.api.rag.modes.agentic.answering import AnswerReview

    client = Mock()
    client.with_options.return_value = client
    client.chat.completions.parse.return_value = parsed_completion(SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        choices=[SimpleNamespace(message=SimpleNamespace(
            content='{"claims":[],"requirements":[],"unplanned_requests":[]}'))]), AnswerReview)
    monkeypatch.setattr(retrieval, "openai_client", Mock(return_value=client))
    result = retrieval._agentic_structured_request([], AnswerReview, "verify", "gpt-5-mini")

    assert result.claims == []
    client.with_options.assert_called_once_with(timeout=60, max_retries=0)
    kwargs = client.chat.completions.parse.call_args.kwargs
    assert kwargs["response_format"] is AnswerReview
    assert kwargs["max_completion_tokens"] == retrieval.config.AGENT_VERIFIER_MAX_COMPLETION_TOKENS
    assert kwargs["reasoning_effort"] == retrieval.config.AGENT_VERIFIER_REASONING_EFFORT
    assert client.chat.completions.parse.call_count == 1


@pytest.mark.parametrize("omit_original", [False, True])
def test_agentic_provider_round_trip_enforces_required_coverage_keys(runtime, monkeypatch,
                                                                   omit_original):
    import json
    from src.api.rag.modes.agentic.answering import _parse_review, _review_schema
    from src.api.rag.modes.agentic.contracts import AnswerRequirement

    retrieval, _ = runtime
    requirements = [
        AnswerRequirement(id="r1", description="Report the measured mass."),
        AnswerRequirement(id="q_original", description="Report mass and uncertainty."),
    ]
    schema = _review_schema(requirements)
    coverage = {row.id: {"status": "missing", "claim_indices": [], "feedback": "Not answered."}
                for row in requirements}
    if omit_original:
        coverage.pop("q_original")
    client = Mock()
    client.with_options.return_value = client
    raw = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(
            refusal=None, content=json.dumps({"claims": [], "requirements": coverage,
                                             "unplanned_requests": []})))])
    if omit_original:
        from pydantic import ValidationError
        try:
            parsed_completion(raw, schema)
        except ValidationError as error:
            client.chat.completions.parse.side_effect = error
    else:
        client.chat.completions.parse.return_value = parsed_completion(raw, schema)
    monkeypatch.setattr(retrieval, "openai_client", Mock(return_value=client))

    if omit_original:
        with pytest.raises(retrieval.AgenticStructuredOutputError) as caught:
            retrieval._agentic_structured_request([], schema, "verify", "gpt-5-mini")
        assert "requirements.q_original" in caught.value.safe_diagnostics["validation_error_locations"]
    else:
        result = _parse_review(
            retrieval._agentic_structured_request([], schema, "verify", "gpt-5-mini"), schema)
        assert [row.requirement_id for row in result.requirements] == ["r1", "q_original"]

    sent_model = client.chat.completions.parse.call_args.kwargs["response_format"]
    assert sent_model is schema
    sent = sent_model.model_json_schema()
    assert set(sent["$defs"]["RequiredCoverage"]["required"]) == {"r1", "q_original"}
    for field in sent["$defs"]["RequiredCoverage"]["properties"].values():
        # Pydantic permits description + $ref; the observed OpenAI endpoint does not.
        assert field == {"$ref": "#/$defs/CoverageCheck"}
    assert client.chat.completions.parse.call_count == 1


@pytest.mark.parametrize("contract", ["review", "reference_judge", "grounding_judge", "draft"])
def test_structured_answer_and_judge_schemas_use_standalone_resolved_refs(runtime, contract):
    from evals.run_benchmark import _reference_judge_schema, GroundingJudgeResult
    from src.api.rag.modes.agentic.answering import _review_schema
    from src.api.rag.modes.agentic.contracts import AnswerRequirement

    retrieval, _ = runtime
    schemas = {
        "review": _review_schema([
            AnswerRequirement(id="r1", description="Report the measured mass."),
            AnswerRequirement(id="q_original", description="Report mass and uncertainty."),
        ]),
        "reference_judge": _reference_judge_schema([
            ("q_1", "Report mass."), ("q_2", "Report uncertainty."),
        ]),
        "grounding_judge": GroundingJudgeResult,
        "draft": retrieval.RAGGenerationResponse,
    }
    schema = schemas[contract].model_json_schema()

    def check(node):
        if isinstance(node, dict):
            if "$ref" in node:
                assert set(node) == {"$ref"}, "OpenAI rejected siblings beside $ref"
                assert node["$ref"].startswith("#/$defs/")
                assert node["$ref"].split("/")[-1] in schema["$defs"]
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node.get("required", [])) == set(node.get("properties", {}))
            for value in node.values():
                check(value)
        elif isinstance(node, list):
            for value in node:
                check(value)

    check(schema)


@pytest.mark.parametrize("stage,model,effort,expected", [
    ("draft", "gpt-5-mini", "low", "low"),
    ("repair", "gpt-5-mini", "minimal", "minimal"),
    ("draft", "gpt-5-mini", "", None),
    ("draft", "gpt-4.1", "low", None),
    ("verify", "gpt-5-mini", "low", "minimal"),
])
def test_agentic_draft_reasoning_is_opt_in_and_independent_of_review(runtime, monkeypatch,
                                                                  stage, model, effort, expected):
    retrieval, _ = runtime
    client = Mock()
    client.with_options.return_value = client
    client.chat.completions.parse.return_value = parsed_completion(SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"claims":[]}'))]),
        retrieval.RAGGenerationResponse)
    monkeypatch.setattr(retrieval, "openai_client", Mock(return_value=client))
    monkeypatch.setattr(retrieval.config, "AGENT_DRAFT_REASONING_EFFORT", effort)
    monkeypatch.setattr(retrieval.config, "AGENT_VERIFIER_REASONING_EFFORT", "minimal")
    retrieval._agentic_structured_request([], retrieval.RAGGenerationResponse, stage, model)
    kwargs = client.chat.completions.parse.call_args.kwargs
    assert kwargs.get("reasoning_effort") == expected
    assert kwargs["max_completion_tokens"] == (
        retrieval.config.AGENT_VERIFIER_MAX_COMPLETION_TOKENS if stage == "verify"
        else retrieval.config.GENERATION_MODEL_MAX_TOKENS)
    assert client.chat.completions.parse.call_count == 1


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
    diagnostics = {"status": "partial", "requirements": []} if mode == "agentic" else None
    pipeline = Mock(return_value={"answer": "Evidence", "sources": [], "images": [],
                                 "generation_diagnostics": diagnostics})
    monkeypatch.setattr(router, "rag_pipeline_wrapper", pipeline)
    monkeypatch.setattr(router, "add_message", Mock())
    monkeypatch.setattr(router, "get_memory", Mock(return_value=SimpleNamespace(summary="", recent_messages=[])))
    monkeypatch.setattr(router, "_process_images", Mock(return_value=[]))
    monkeypatch.setattr(papers_router, "active_corpus", lambda: (
        SimpleNamespace(PAPERS_COLLECTION="papers"), [{"id": "ready-1"}], "snapshot-1"))
    result = asyncio.run(router.rag(request(), RAGRequest(query="Compare papers", mode=mode, corpus="arxiv"), Response()))
    assert result.mode == mode
    assert result.generation_diagnostics == diagnostics
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


@pytest.mark.parametrize("call_timings", [
    {}, {"draft_seconds": 2.0, "verify_seconds": 3.0},
    {"draft_seconds": 2.0, "verify_seconds": 6.0, "repair_seconds": 1.0},
])
def test_successful_agentic_execution_reaches_reviewed_generator_and_trace(runtime, monkeypatch,
                                                                         call_timings):
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
    from src.api.rag.modes.agentic.answering import AgenticAnswer
    claim = retrieval.RAGClaim(text="Grounded", cited_context_ids=["point"], need_ids=[])
    response = retrieval.RAGGenerationResponse(claims=[claim])
    monkeypatch.setattr(retrieval, "generate_agentic_answer", Mock(return_value=
        AgenticAnswer(response, {"status": "complete", "stage_timings": call_timings}, [])))
    update = Mock()
    monkeypatch.setattr(retrieval, "update_span", update)

    timings = {}
    result = retrieval.rag_pipeline(
        "question", Mock(), "session", mode="agentic", collection="papers",
        scope=RetrievalScope("papers", ("build",)), catalogue=Mock(), agent_model=Mock(),
        stage_timings=timings,
    )

    assert result["answer"] == "Grounded [1]"
    assert result["sources"][0].id == "point"
    assert result["execution"].stop_reason.value == "sufficient"
    assert {key: value for key, value in timings.items() if key.startswith("agentic_")} == {
        f"agentic_{key}": value for key, value in call_timings.items()
    }
    assert timings["generation_seconds"] >= 0
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
        retrieval, "generate_agentic_answer", Mock(side_effect=ValueError("invalid citations")),
    )

    with pytest.raises(ValueError) as caught:
        retrieval.rag_pipeline(
            "question", Mock(), "session", mode="agentic", collection="papers",
            scope=RetrievalScope("papers", ("build",)), catalogue=Mock(), agent_model=Mock(),
        )

    assert caught.value.agent_execution.synthesis_policy == "evidence_fallback"


def test_citation_validation_exhaustion_returns_observable_safe_abstention(
        runtime, monkeypatch):
    retrieval, _ = runtime
    contexts = [{
        "id": "point", "paper_id": "paper", "title": "Named Scientific Paper",
        "authors": ["Author"], "year": 2026, "page": 2, "text": "Partial evidence",
    }]
    monkeypatch.setattr(retrieval, "retrieve_context", Mock(return_value=contexts))
    monkeypatch.setattr(retrieval, "build_prompt", Mock(return_value=[]))
    validation_error = retrieval.InvalidCitationIdsError("unknown_context_id")
    validation_error.validation_failures = [{
        "code": "unknown_context_id",
        "exception_type": "InvalidCitationIdsError",
    }]
    monkeypatch.setattr(
        retrieval, "generate_answer",
        Mock(side_effect=validation_error),
    )

    result = retrieval.rag_pipeline(
        'What does "Named Scientific Paper" report?', Mock(), "session",
        mode="hybrid", collection="papers", scope="ready",
    )

    assert "abstained" in result["answer"]
    assert result["retrieved_chunks"] == contexts
    assert result["cited_context_ids"] == []
    assert result["sources"] == []
    assert result["generation_diagnostics"] == {
        "status": "safe_abstention",
        "reason": "citation_validation_failed",
        "exception_type": "InvalidCitationIdsError",
        "attempts": 2,
        "validation_failures": [{
            "code": "unknown_context_id",
            "exception_type": "InvalidCitationIdsError",
        }],
    }


def test_explicit_modes_abstain_before_generation_when_named_paper_is_missing(
        runtime, monkeypatch):
    retrieval, _ = runtime
    from src.api.rag.contracts import RetrievalScope, ScopedBuild

    scope = RetrievalScope("papers", ("build-a", "build-b"), kind="frozen", builds=(
        ScopedBuild("build-a", "paper-a"), ScopedBuild("build-b", "paper-b"),
    ))
    rows = [
        {"id": "build-a", "paper_id": "paper-a", "source": "arxiv",
         "source_id": "a", "active_build": "build-a", "deleted": 0,
         "collection": "papers", "version": 1, "status": "ready",
         "metadata": {"title": "First named scientific paper"}},
        {"id": "build-b", "paper_id": "paper-b", "source": "arxiv",
         "source_id": "b", "active_build": "build-b", "deleted": 0,
         "collection": "papers", "version": 1, "status": "ready",
         "metadata": {"title": "Second named scientific paper"}},
    ]
    contexts = [{
        "id": "a1", "build_id": "build-a", "paper_id": "paper-a",
        "title": "First named scientific paper", "text": "Only the first paper.",
    }]
    monkeypatch.setattr(retrieval, "retrieve_context", Mock(return_value=contexts))
    generate = Mock()
    monkeypatch.setattr(retrieval, "generate_answer", generate)

    result = retrieval.rag_pipeline(
        'Compare "First named scientific paper" and "Second named scientific paper".',
        Mock(), "session", mode="hybrid", collection="papers", scope=scope,
        catalogue=SimpleNamespace(all_builds=lambda: rows),
    )

    assert "every explicitly named paper" in result["answer"]
    assert result["generation_diagnostics"]["reason"] == "named_paper_coverage_failed"
    assert result["generation_diagnostics"]["missing_build_ids"] == ["build-b"]
    assert result["retrieved_chunks"] == contexts
    generate.assert_not_called()
