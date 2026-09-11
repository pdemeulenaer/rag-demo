"""Offline evidence sampling and generation contracts; no paid APIs or live services."""
from collections import Counter
from copy import deepcopy
import json
import random
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from evals import generate_questions as gen


def chunk(eid="e1", paper="p1"):
    return {"evidence_id": eid, "paper_id": paper, "build_id": "b" + paper,
            "collection": "arxiv", "point_id": eid, "title": "Cluster masses",
            "text": "The estimated mass is 100 solar masses. " * 5}


def proposal(eids=("e1",), question="What mass was estimated?"):
    return gen.Proposal(candidate=gen.Question(question=question,
        reference_answer="100 solar masses.", support_summary="The excerpt states the mass.",
        citations=[gen.Citation(evidence_id=eid, quote="100 solar masses") for eid in eids]), skip_reason=None)


def test_plan_balanced_deterministic_and_two_distinct_papers():
    papers = [{"paper_id": f"p{i}", "build_id": f"b{i}", "title": "Cluster masses",
               "abstract": "Stellar dynamics", "evidence_ids": [f"e{i}"]} for i in range(50)]
    jobs = gen.plan_jobs(papers, 50, 42)
    assert jobs == gen.plan_jobs(list(reversed(papers)), 50, 42)
    assert Counter(j["kind"] for j in jobs) == {
        "single_paper": 30, "cross_paper": 15, "unanswerable_candidate": 5}
    assert len({eid for job in jobs for eid in job["evidence_ids"]}) == 50
    for job in jobs:
        if job["kind"] == "cross_paper":
            assert len(set(job["evidence_ids"])) == 2
    with pytest.raises(ValueError, match="At least two"):
        gen.plan_jobs(papers[:1], 50, 42)


def test_active_sources_delegate_to_scoped_model_compatible_catalogue():
    catalogue = Mock()
    catalogue.active.side_effect = [[{"id": "a"}], [{"id": "u"}]]
    settings = object()
    options = SimpleNamespace(QDRANT_COLLECTION_NAME="uploads")
    assert gen.active_builds(catalogue, settings, options, "all") == [
        {"id": "a", "source": "arxiv"}, {"id": "u", "source": "uploads"}]
    assert catalogue.active.call_args_list[0].args == (settings,)
    assert catalogue.active.call_args_list[1].kwargs == {"source": "uploads", "collection": "uploads"}


def indexed_build():
    return {"id": "build", "paper_id": "paper", "version": 1, "source": "arxiv",
            "embedding_model": "text-embedding-3-small",
            "collection": "science", "metadata": {"title": "Cluster mass"},
            "manifest": {"point_ids": [str(i) for i in range(260)], "chunk_count": 260}}


def indexed_client(build):
    def retrieve(**kwargs):
        return [SimpleNamespace(id=pid, payload={"build_id": build["id"],
            "paper_id": build["paper_id"], "paper_version": 1, "page_number": 2,
            "type": "text" if pid % 3 == 0 else ("summary" if pid % 3 == 1 else "figure"),
            "text": "Measured stellar populations and cluster masses. " * 100})
            for pid in reversed(kwargs["ids"])]
    return SimpleNamespace(retrieve=Mock(side_effect=retrieve))


def test_sample_paginated_manifest_only_text_and_bounded():
    build = indexed_build()
    client = indexed_client(build)
    chunks = gen.sample_evidence(client, build, random.Random(42), 4)
    assert client.retrieve.call_count == 3
    assert len(chunks) == 4
    assert all(int(c["point_id"]) % 3 == 0 and len(c["text"]) == 2400 for c in chunks)
    assert all(c["page_number"] == 2 and c["build_id"] == "build" for c in chunks)
    for call in client.retrieve.call_args_list:
        assert len(call.kwargs["ids"]) <= 128
        assert call.kwargs["with_vectors"] is False
        assert call.kwargs["collection_name"] == "science"
    assert gen.sample_evidence(indexed_client(build), build, random.Random(42), 4) == chunks


@pytest.mark.parametrize("fault", ["missing", "identity", "empty_manifest"])
def test_bad_index_fails_closed(fault):
    build = indexed_build()
    client = indexed_client(build)
    if fault == "missing":
        client.retrieve.side_effect = lambda **kwargs: []
    elif fault == "identity":
        client.retrieve.side_effect = lambda **kwargs: [SimpleNamespace(id=pid, payload={}) for pid in kwargs["ids"]]
    else:
        build["manifest"] = {}
    with pytest.raises(ValueError, match="make papers-audit"):
        gen.sample_evidence(client, build, random.Random(42), 4)


def test_uploaded_chunk_payload_is_supported():
    build = indexed_build()
    build["source"] = "uploads"
    build["manifest"]["point_ids"] = ["1"]
    client = Mock()
    client.retrieve.return_value = [SimpleNamespace(id=1, payload={"build_id": "build",
        "paper_id": "paper", "paper_version": 1, "type": "chunk", "text": chunk()["text"]})]
    result = gen.sample_evidence(client, build, random.Random(42), 4)
    assert len(result) == 1 and result[0]["source"] == "uploads"


def test_validation_exact_quotes_refs_dedup_and_review_status():
    evidence = {"e1": chunk()}
    job = {"id": "q1", "kind": "single_paper", "evidence_ids": ["e1"]}
    seen = set()
    candidate = gen.validate_candidate(proposal(), job, evidence, seen)
    assert candidate["review_status"] == "needs_review"
    assert candidate["reference_evidence"] == [evidence["e1"]]
    with pytest.raises(ValueError, match="duplicate_question"):
        gen.validate_candidate(proposal(), job, evidence, seen)
    with pytest.raises(ValueError, match="unknown_evidence"):
        gen.validate_candidate(proposal(["made-up"]), job, evidence, set())
    bad_quote = proposal()
    bad_quote.candidate.citations[0].quote = "999 solar masses"
    with pytest.raises(ValueError, match="quote_not_in_evidence"):
        gen.validate_candidate(bad_quote, job, evidence, set())


def test_cross_paper_needs_two_papers_not_two_chunks():
    evidence = {"e1": chunk(), "e2": chunk("e2", "p1")}
    job = {"id": "q2", "kind": "cross_paper", "evidence_ids": list(evidence)}
    with pytest.raises(ValueError, match="wrong_number"):
        gen.validate_candidate(proposal(["e1", "e2"]), job, evidence, set())
    evidence["e2"]["paper_id"] = "p2"
    assert len(gen.validate_candidate(proposal(["e1", "e2"]), job, evidence, set())["reference_evidence"]) == 2


def test_negative_has_no_positive_evidence_and_is_not_corpus_ground_truth():
    job = {"id": "q3", "kind": "unanswerable_candidate", "evidence_ids": ["e1"]}
    result = gen.validate_candidate(proposal([]), job, {"e1": chunk()}, set())
    assert result["answerability_scope"] == "supplied_excerpts_only"
    assert result["reference_evidence"] == []
    assert result["generation_evidence_ids"] == ["e1"]
    with pytest.raises(ValueError, match="wrong_number"):
        gen.validate_candidate(proposal(), job, {"e1": chunk()}, set())


@pytest.fixture
def prepared(tmp_path):
    snapshot = {"evidence": [chunk(), chunk("e2", "p2")]}
    jobs = [
        {"id": "q1", "kind": "single_paper", "evidence_ids": ["e1"]},
        {"id": "q2", "kind": "cross_paper", "evidence_ids": ["e1", "e2"]},
        {"id": "q3", "kind": "unanswerable_candidate", "evidence_ids": ["e2"]},
    ]
    plan = {"schema_version": 1, "snapshot_hash": gen.digest(snapshot), "jobs": jobs,
            "model": "test-model", "prompt": gen.SYSTEM_PROMPT, "max_completion_tokens": 2500}
    gen.write_json(tmp_path / "snapshot.json", snapshot)
    gen.write_json(tmp_path / "plan.json", plan)
    return tmp_path


def fake_client():
    client = MagicMock()
    client.__enter__.return_value = client
    def parse(**kwargs):
        context = json.loads(kwargs["input"])
        eids = [] if context["kind"] == "unanswerable_candidate" else [e["evidence_id"] for e in context["excerpts"]]
        return SimpleNamespace(id="response", model="test-model-version", status="completed", output=[],
            usage=SimpleNamespace(model_dump=lambda: {"total_tokens": 100}),
            output_text=proposal(eids, question=f"Scientific question for {context['kind']}?").model_dump_json())
    client.responses.create.side_effect = parse
    return client


def test_generation_checkpoints_and_completed_rerun_is_free(prepared):
    client = fake_client()
    gen.generate(prepared, lambda: client)
    assert client.responses.create.call_count == 3
    questions = json.loads((prepared / "questions.json").read_text())["questions"]
    assert len(questions) == 3
    assert all(q["review_status"] == "needs_review" for q in questions)
    for call in client.responses.create.call_args_list:
        assert call.kwargs["text"]["format"]["schema"] == gen.Proposal.model_json_schema()
        assert call.kwargs["background"] is True
        assert call.kwargs["store"] is False
        assert call.kwargs["max_output_tokens"] == 2500
    factory = Mock(side_effect=AssertionError("Completed run must not create a client"))
    gen.generate(prepared, factory)
    factory.assert_not_called()
    assert not (prepared / ".generating").exists()


def test_failure_keeps_checkpoint_and_resume_skips_success(prepared):
    client = fake_client()
    parse = client.responses.create.side_effect
    responses = 0
    def fail_second(**kwargs):
        nonlocal responses
        responses += 1
        if responses == 2:
            raise RuntimeError("API unavailable")
        return parse(**kwargs)
    client.responses.create.side_effect = fail_second
    with pytest.raises(RuntimeError, match="API unavailable"):
        gen.generate(prepared, lambda: client)
    assert len(json.loads((prepared / "results.json").read_text())["results"]) == 1
    failure = json.loads((prepared / "last_error.json").read_text())
    assert failure["job_id"] == "q2"
    assert failure["causes"] == [{"type": "RuntimeError"}]
    assert failure["elapsed_seconds"] >= 0
    assert not (prepared / ".generating").exists()
    retry = fake_client()
    with pytest.raises(gen.BackgroundError, match="submission outcome unknown"):
        gen.generate(prepared, lambda: retry)
    retry.responses.create.assert_not_called()
    gen.generate(prepared, lambda: retry, retry_job="q2")
    assert retry.responses.create.call_count == 2


def test_refusals_checkpointed_not_retried(prepared):
    client = fake_client()
    client.responses.create.side_effect = None
    client.responses.create.return_value = SimpleNamespace(id="refusal", model="test", usage=None,
        status="completed", output_text="", output=[SimpleNamespace(type="message",
            content=[SimpleNamespace(type="refusal", refusal="refused")])])
    gen.generate(prepared, lambda: client)
    state = json.loads((prepared / "results.json").read_text())
    assert all(r["rejection"] == "model_refused_or_no_parsed_output" for r in state["results"])
    gen.generate(prepared, Mock(side_effect=AssertionError("Must not retry refusals")))


def test_tampered_snapshot_fails_before_model(prepared):
    gen.write_json(prepared / "snapshot.json", {"evidence": []})
    with pytest.raises(ValueError, match="Snapshot changed"):
        gen.generate(prepared, Mock(side_effect=AssertionError("No model calls")))


def test_changed_plan_fails_on_resume(prepared):
    gen.generate(prepared, fake_client)
    plan = json.loads((prepared / "plan.json").read_text())
    plan["model"] = "different-model"
    gen.write_json(prepared / "plan.json", plan)
    with pytest.raises(ValueError, match="Plan changed"):
        gen.generate(prepared, Mock(side_effect=AssertionError("No model calls")))
    assert not (prepared / ".generating").exists()


def test_concurrent_run_refused_without_removing_its_lock(prepared):
    (prepared / ".generating").touch()
    with pytest.raises(FileExistsError):
        gen.generate(prepared, Mock(side_effect=AssertionError("No model calls")))
    assert (prepared / ".generating").exists()


@pytest.mark.parametrize("drift", [False, True])
def test_prepare_freezes_active_only_and_does_not_overwrite(tmp_path, monkeypatch, drift):
    build = indexed_build()
    second = {**deepcopy(build), "id": "build2", "paper_id": "paper2"}
    second["manifest"]["point_ids"] = ["300"]
    catalogue = Mock()
    catalogue.active.return_value = [build, second]
    if drift:
        catalogue.active.side_effect = [[build, second], []]
    monkeypatch.setattr(gen, "Catalogue", Mock(return_value=catalogue))
    options = gen.EvaluationSettings(_env_file=None, OPENAI_API_KEY="")
    monkeypatch.setattr(gen, "EvaluationSettings", lambda: options)
    client = indexed_client(build)
    first_retrieve = client.retrieve.side_effect
    def retrieve(**kwargs):
        points = first_retrieve(**kwargs)
        for point in points:
            if point.id == 300:
                point.payload.update(build_id="build2", paper_id="paper2")
        return points
    client.retrieve.side_effect = retrieve
    client.close = Mock()
    import qdrant_client
    monkeypatch.setattr(qdrant_client, "QdrantClient", Mock(return_value=client))
    args = SimpleNamespace(output=tmp_path / "preview", source="arxiv", papers=50,
                           seed=42, chunks_per_paper=4, questions=50, model="test-model",
                           max_completion_tokens=25000)
    if drift:
        with pytest.raises(gen.EvaluationError, match="Active corpus changed"):
            gen.prepare(args)
        assert not args.output.exists()
        catalogue.close.assert_called_once()
        return
    gen.prepare(args)
    snapshot = json.loads((args.output / "snapshot.json").read_text())
    plan = json.loads((args.output / "plan.json").read_text())
    assert len(snapshot["papers"]) == 2
    assert len(plan["jobs"]) == 50
    assert plan["max_completion_tokens"] == 25000
    assert plan["snapshot_hash"] == gen.digest(snapshot)
    assert not (args.output / "questions.json").exists()
    assert catalogue.method_calls[0][0] == "require_schema"
    catalogue.close.assert_called_once()
    before = (args.output / "snapshot.json").read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        gen.prepare(args)
    assert (args.output / "snapshot.json").read_bytes() == before


@pytest.mark.parametrize("token_limit", [2500, 25000])
def test_real_openai_sdk_structured_output_contract_without_network(prepared, token_limit, monkeypatch):
    import httpx
    from openai import OpenAI
    from evals import background
    monkeypatch.setattr(background, "sleep", lambda seconds: None)

    plan = json.loads((prepared / "plan.json").read_text())
    plan["max_completion_tokens"] = token_limit
    gen.write_json(prepared / "plan.json", plan)
    requests = []
    responses = {}
    def respond(request):
        if request.method == "GET":
            return httpx.Response(200, json=responses[request.url.path.rsplit("/", 1)[1]])
        assert request.method == "POST" and request.url.path == "/v1/responses"
        body = json.loads(request.content)
        requests.append(body)
        assert body["text"]["format"]["type"] == "json_schema"
        assert body["text"]["format"]["strict"] is True
        assert body["background"] is True
        assert body["store"] is False
        assert body["max_output_tokens"] == token_limit
        context = json.loads(body["input"])
        eids = [] if context["kind"] == "unanswerable_candidate" else [e["evidence_id"] for e in context["excerpts"]]
        content = proposal(eids, question=f"Question about {context['kind']}?").model_dump_json()
        response_id = f"resp_{len(requests)}"
        value = {"id": response_id, "object": "response", "created_at": 0, "model": "test-model",
            "status": "completed", "output": [{"type": "message", "id": "msg_test", "role": "assistant",
                "status": "completed", "content": [{"type": "output_text", "text": content, "annotations": []}]}],
            "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150,
                      "input_tokens_details": {"cached_tokens": 0}, "output_tokens_details": {"reasoning_tokens": 10}}}
        responses[response_id] = value
        return httpx.Response(200, json={**value, "status": "queued", "output": [], "usage": None})

    gen.generate(prepared, lambda: OpenAI(api_key="offline-test", max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(respond))))
    assert len(requests) == 3
    assert len(json.loads((prepared / "questions.json").read_text())["questions"]) == 3


@pytest.mark.parametrize("value", ["0", "-1", "255", "128001", "not-an-integer"])
def test_cli_rejects_invalid_token_limit_before_service_access(monkeypatch, value):
    prepare = Mock(side_effect=AssertionError("No service access expected"))
    monkeypatch.setattr(gen, "prepare", prepare)
    monkeypatch.setattr("sys.argv", ["generate_questions", "prepare", f"--max-completion-tokens={value}"])
    with pytest.raises(SystemExit) as error:
        gen.main()
    assert error.value.code == 2
    prepare.assert_not_called()


@pytest.mark.parametrize("arguments,expected", [([], 2500), (["--max-completion-tokens", "25000"], 25000)])
def test_cli_token_limit_default_and_override(monkeypatch, arguments, expected):
    prepare = Mock()
    monkeypatch.setattr(gen, "prepare", prepare)
    monkeypatch.setattr("sys.argv", ["generate_questions", "prepare", *arguments])
    gen.main()
    assert prepare.call_args.args[0].max_completion_tokens == expected


def test_read_only_connectivity_check_uses_saved_model_without_writes(prepared, capsys):
    before = {path.name: path.read_bytes() for path in prepared.iterdir()}
    client = MagicMock()
    client.__enter__.return_value = client
    gen.check_connection(prepared, lambda: client)
    client.models.retrieve.assert_called_once_with("test-model")
    client.responses.create.assert_not_called()
    assert {path.name: path.read_bytes() for path in prepared.iterdir()} == before
    result = json.loads(capsys.readouterr().out)
    assert result["model_metadata_reachable"] is True and result["generation_calls"] == 0


@pytest.mark.parametrize("cause,category", [
    ("dns", "dns"), ("tls", "tls"), ("timeout", "timeout"),
    ("disconnect", "connection_interrupted"), ("local_protocol", "request_configuration"),
])
def test_error_diagnostics_classify_causes_without_secrets(cause, category):
    import httpx
    import socket
    import ssl
    from openai import APIConnectionError
    from evals.diagnostics import error_details

    secret = "sk-private-key https://user:password@example.com/private?token=secret private-paper-text"
    exceptions = {"dns": socket.gaierror(-2, secret), "tls": ssl.SSLCertVerificationError(1, secret),
        "timeout": httpx.ReadTimeout(secret), "disconnect": httpx.RemoteProtocolError(secret),
        "local_protocol": httpx.LocalProtocolError(secret)}
    error = APIConnectionError(request=httpx.Request("POST", "https://example.com/private"), message=secret)
    error.__cause__ = exceptions[cause]
    details = error_details(error)
    assert details["category"] == category
    assert len(details["causes"]) == 2
    serialized = json.dumps(details)
    for value in ("sk-private", "password", "example.com", "private-paper-text", "token=secret"):
        assert value not in serialized


def test_connectivity_failure_reports_cause_and_preserves_files(prepared, capsys):
    import httpx
    client = MagicMock()
    client.__enter__.return_value = client
    client.models.retrieve.side_effect = httpx.ConnectError("private endpoint with secret")
    before = {p.name: p.read_bytes() for p in prepared.iterdir()}
    with pytest.raises(httpx.ConnectError):
        gen.check_connection(prepared, lambda: client)
    captured = capsys.readouterr().out
    assert "secret" not in captured
    assert json.loads(captured)["category"] == "connection"
    assert {p.name: p.read_bytes() for p in prepared.iterdir()} == before


def test_error_diagnostics_handle_cycles():
    from evals.diagnostics import error_details
    first, second = RuntimeError("private"), RuntimeError("private")
    first.__cause__, second.__cause__ = second, first
    assert len(error_details(first)["causes"]) == 2


def test_legacy_checkpoint_is_preserved_and_new_results_use_background(prepared):
    plan_before = (prepared / "plan.json").read_bytes()
    snapshot_before = (prepared / "snapshot.json").read_bytes()
    plan = json.loads(plan_before)
    old_result = {"id": "q1", "candidate": None, "rejection": "quote_not_in_evidence",
                  "response_id": "old-chat-response", "kind": "single_paper", "model": "gpt-5"}
    gen.write_json(prepared / "results.json", {"plan_hash": gen.digest(plan), "results": [old_result]})
    client = fake_client()
    gen.generate(prepared, lambda: client)
    assert client.responses.create.call_count == 2
    state = json.loads((prepared / "results.json").read_text())
    assert state["results"][0] == old_result
    assert state["results"][1]["transport"] == "responses-background-v1"
    assert (prepared / "plan.json").read_bytes() == plan_before
    assert (prepared / "snapshot.json").read_bytes() == snapshot_before


@pytest.mark.parametrize("value", ["0", "4", "3601", "invalid"])
def test_cli_rejects_bad_polling_limit(monkeypatch, value):
    generate = Mock(side_effect=AssertionError("No model calls"))
    monkeypatch.setattr(gen, "generate", generate)
    monkeypatch.setattr("sys.argv", ["generate_questions", "generate", "--wait-seconds", value])
    with pytest.raises(SystemExit) as error:
        gen.main()
    assert error.value.code == 2
    generate.assert_not_called()
