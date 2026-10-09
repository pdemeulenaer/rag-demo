"""Real GraphRAG component + SDK parsing with fake HTTP; no .env/live providers."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from threading import Barrier, Lock
from uuid import NAMESPACE_URL, uuid5

import httpx
from openai import OpenAI
import pytest

# The online stack intentionally excludes this optional extraction dependency.
pytest.importorskip("neo4j_graphrag")

from src.api.kg.artifacts import VerifiedReader, load_paper
from src.api.kg.contracts import SourceChunk
from src.api.kg.extraction import CandidateRecords, ScientificExtractor, REVISION
from src.api.kg.extraction import ScientificResult, bind_sources, staging_graph
from src.api.kg import jobs
from src.api.kg.settings import KGSettings


PAPER = "00000000-0000-0000-0000-000000000001"
BUILD = "00000000-0000-0000-0000-000000000002"


@pytest.fixture
def corpus(tmp_path):
    settings = KGSettings(_env_file=None, PAPERS_ARTIFACT_DIR=tmp_path / "artifacts",
                          PAPERS_STORAGE_MODE="LOCAL", OPENAI_API_KEY="test-not-real",
                          LANGFUSE_ENABLED=False)

    def save(name, value):
        data = value.encode() if isinstance(value, str) else json.dumps(value).encode()
        digest = sha256(data).hexdigest()
        path = settings.PAPERS_ARTIFACT_DIR / "builds" / BUILD / digest / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return dict(uri=str(path), sha256=digest, bytes=len(data))

    chunks = [dict(chunk_index=i, page_number=1, section_header="Results",
                   text=f"M22 has distance {3 + i}.27 ± 0.14 kpc.") for i in range(3)]
    manifest = dict(collection="arxiv_papers_v2", embedding_model="text-embedding-3-small",
                    pipeline_id="test-pipeline", extraction={"version": "test"}, chunk_count=3,
                    chunk_order=dict(field="chunk_index", count=3, starts_at=0,
                                     contiguous=True, scope="text_chunks"),
                    text=save("chunks.json", chunks),
                    pages=save("pages.json", [dict(page_number=1, text="markdown")]),
                    markdown=save("document.md", "markdown"))
    manifest["artifact"] = save("manifest.json", manifest)
    row = dict(paper_id=PAPER, source="arxiv", version=1, deleted=0,
               manifest=manifest, collection=manifest["collection"],
               pipeline_id=manifest["pipeline_id"], embedding_model=manifest["embedding_model"])
    paper = dict(paper_id=PAPER, build_id=BUILD, source="arxiv", version=1,
                 collection=manifest["collection"], title="M22 study", group="M22")
    class Catalogue:
        def scoped_ready_builds(self, collection, builds, *, active_only):
            assert collection == paper["collection"] and builds == [BUILD]
            assert active_only is False
            return [row]
    return SimpleNamespace(settings=settings, reader=VerifiedReader(settings), save=save,
        row=row, paper=paper, catalogue=Catalogue(), directory=tmp_path / "kg",
        selection=dict(papers=[paper], corpus_fingerprint="test-corpus"))


def records(text="M22 has distance 3.27 ± 0.14 kpc."):
    evidence = [dict(quote=text)]
    return dict(entities=[dict(id="m22", kind="astronomical_object", name="M22", aliases=[], evidence=evidence)],
        observations=[dict(id="distance", subject_id="m22", kind="measurement", statement=text,
            quantity="distance", value_text="3.27", unit_text="kpc", uncertainty_text="± 0.14",
            conditions=[], evidence=evidence)], relationships=[])


def sdk_component(settings, responses):
    requests = []
    def transport(request):
        payload = json.loads(request.content)
        requests.append(payload)
        result = responses[len(requests) - 1]
        if isinstance(result, Exception):
            raise result
        message = {"role": "assistant", "content": json.dumps(result)}
        if result == "refuse":
            message = {"role": "assistant", "content": None, "refusal": "test refusal"}
        return httpx.Response(200, json={"id": "chat-test", "object": "chat.completion",
            "created": 0, "model": "gpt-5-mini-test", "choices": [dict(index=0,
                finish_reason="stop", message=message)],
            "usage": dict(prompt_tokens=100, completion_tokens=50, total_tokens=150)})
    client = OpenAI(api_key="test-not-real", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(transport)))
    return ScientificExtractor(client, settings), requests, client


def prepare(corpus):
    return jobs.prepare(corpus.directory, corpus.selection, corpus.catalogue,
                        corpus.reader, corpus.settings)


def test_full_artifacts_not_sampled_evidence(corpus):
    chunks, digest = load_paper(corpus.paper, corpus.catalogue, corpus.reader)
    assert len(chunks) == 3
    assert str(chunks[2].point_id) == str(uuid5(NAMESPACE_URL, f"{BUILD}:2"))
    assert digest == corpus.row["manifest"]["artifact"]["sha256"]


@pytest.mark.parametrize("field,value", [("paper_id", BUILD), ("source", "uploads"),
                                        ("version", 2), ("deleted", 1)])
def test_sql_scope_fail_closed(corpus, field, value):
    corpus.row[field] = value
    with pytest.raises(ValueError, match="identity/version"):
        prepare(corpus)
    assert not corpus.directory.exists()


def test_absent_frozen_ready_build(corpus):
    corpus.catalogue.scoped_ready_builds = lambda *args, **kwargs: []
    with pytest.raises(ValueError, match="not available/ready"):
        prepare(corpus)


@pytest.mark.parametrize("artifact", ["text", "pages", "markdown", "artifact"])
def test_artifact_hash_failure(corpus, artifact):
    Path(corpus.row["manifest"][artifact]["uri"]).write_text("corrupted")
    with pytest.raises(ValueError, match="integrity"):
        prepare(corpus)


def test_container_path_maps_to_host_root(corpus):
    ref = deepcopy(corpus.row["manifest"]["text"])
    ref["uri"] = "/app/paper_artifacts/builds/" + ref["uri"].split("/builds/", 1)[1]
    assert len(corpus.reader.read_json(ref, BUILD, "chunks.json")) == 3


def test_reader_does_not_fetch_arbitrary_url(corpus):
    ref = dict(corpus.row["manifest"]["text"], uri="https://attacker.invalid/chunks.json")
    with pytest.raises(ValueError, match="path"):
        corpus.reader.read_json(ref, BUILD, "chunks.json")


def test_symlink_escape_rejected(corpus, tmp_path):
    ref = corpus.row["manifest"]["text"]
    path = Path(ref["uri"])
    outside = tmp_path / "outside.json"
    outside.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(outside)
    with pytest.raises(ValueError, match="escapes"):
        corpus.reader.read_json(ref, BUILD, "chunks.json")


def test_azure_reader_is_pinned_to_configured_container(corpus):
    ref = deepcopy(corpus.row["manifest"]["text"])
    data = Path(ref["uri"]).read_bytes()
    calls = []
    class Container:
        url = "https://account.blob.core.windows.net/rag-papers"
        def download_blob(self, key):
            calls.append(key)
            return SimpleNamespace(readall=lambda: data)
    corpus.reader.container = Container()
    ref["uri"] = Container.url + "/builds/" + ref["uri"].split("/builds/", 1)[1]
    assert len(corpus.reader.read_json(ref, BUILD, "chunks.json")) == 3
    ref["uri"] = ref["uri"].replace("account.blob", "other.blob")
    with pytest.raises(ValueError, match="configured Azure"):
        corpus.reader.read_json(ref, BUILD, "chunks.json")
    assert len(calls) == 1


def test_prepare_idempotent_no_overwrite_and_frozen_model(corpus):
    first = prepare(corpus)
    assert prepare(corpus) == first
    assert first["model_calls"] == 0 and first["maximum_first_pass_calls"] == 3
    corpus.settings.KG_MODEL = "other-model"
    with pytest.raises(ValueError, match="differs"):
        prepare(corpus)
    with pytest.raises(ValueError, match="settings differ"):
        jobs.read_plan(corpus.directory, corpus.settings)


def test_native_sdk_schema_component_and_resumption(corpus):
    prepare(corpus)
    component, requests, client = sdk_component(corpus.settings, [records(), records("M22 has distance 4.27 ± 0.14 kpc."),
                                                                records("M22 has distance 5.27 ± 0.14 kpc.")])
    try:
        first = jobs.extract(corpus.directory, corpus.settings, max_calls=1, component=component)
        assert first["states"]["complete"] == 1 and first["states"]["pending"] == 2
        second = jobs.extract(corpus.directory, corpus.settings, max_calls=2, component=component)
        assert second["states"]["complete"] == 3
        assert second["known_total_tokens"] == 450
        third = jobs.extract(corpus.directory, corpus.settings, component=component)
        assert third["model_calls_reserved_this_invocation"] == 0 and len(requests) == 3
        assert jobs.validate(corpus.directory)["complete"] is True
        schema = requests[0]["response_format"]["json_schema"]
        assert schema["strict"] is True
        assert schema["schema"]["additionalProperties"] is False
        assert requests[0]["max_completion_tokens"] == 16384
        saved = json.loads((corpus.directory / "candidates.json").read_text())
        batch = saved["chunks"][0]["batch"]
        assert batch["entities"][0]["id"].startswith(f"{BUILD}:{REVISION}:")
        assert batch["observations"][0]["uncertainty_text"] == "± 0.14"
        assert saved["graph_ready"] is False and saved["review_status"] == "needs_review"
    finally:
        client.close()


@pytest.mark.parametrize("bad", ["invented_quote", "missing_node", "refuse", "connection"])
def test_failures_checkpoint_not_silent_retry(corpus, bad):
    prepare(corpus)
    output = records()
    if bad == "invented_quote":
        output["observations"][0]["evidence"] = [dict(quote="not in the source")]
    elif bad == "missing_node":
        output["observations"][0]["subject_id"] = "undeclared"
    elif bad == "refuse":
        output = "refuse"
    else:
        output = httpx.ConnectError("test secret must not be saved")
    component, requests, client = sdk_component(corpus.settings, [output])
    try:
        result = jobs.extract(corpus.directory, corpus.settings, max_calls=1, component=component)
        assert result["states"]["failed"] == 1 and len(requests) == 1
        with sqlite3.connect(corpus.directory / "checkpoints.sqlite") as db:
            failed = db.execute("SELECT id,result,error FROM jobs WHERE status='failed'").fetchone()
            diagnostics = json.loads(failed[1]).get("safe_diagnostics", {})
            if bad in {"invented_quote", "missing_node"}:
                expected = "quote_not_found" if bad == "invented_quote" else "undeclared_observation_subject"
                assert diagnostics["rejection_issues"][0]["code"] == expected
                assert diagnostics["rejection_issues"][0]["path"].startswith("observations.0.")
            # Isolate resumption eligibility: mark the untested remaining jobs interrupted.
            db.execute("UPDATE jobs SET status='interrupted' WHERE status='pending'")
            assert "test secret" not in failed[2]
        resumed = jobs.extract(corpus.directory, corpus.settings, component=component)
        assert resumed["model_calls_reserved_this_invocation"] == 0
        assert jobs.validate(corpus.directory)["validated_chunks"] == 0
        failures = json.loads((corpus.directory / "failures.json").read_text())
        assert len(failures["failures"]) == 3  # Includes the two explicitly interrupted fixture jobs.
        assert "test secret" not in json.dumps(failures)
    finally:
        client.close()


def test_explicit_retry_preserves_attempt_history(corpus):
    prepare(corpus)
    bad = records()
    bad["entities"][0]["evidence"] = [dict(quote="absent")]
    component, requests, client = sdk_component(corpus.settings, [bad, records()])
    try:
        jobs.extract(corpus.directory, corpus.settings, max_calls=1, component=component)
        result = jobs.extract(corpus.directory, corpus.settings, max_calls=1,
                              failed_only=True, component=component)
        assert result["states"]["complete"] == 1 and result["total_attempts_reserved"] == 2
        assert result["known_total_tokens"] == 300
        with sqlite3.connect(corpus.directory / "checkpoints.sqlite") as db:
            assert [row[0] for row in db.execute("SELECT status FROM attempts ORDER BY attempt")] == ["failed", "complete"]
    finally:
        client.close()


def test_diagnostics_cover_all_rejected_records_without_raw_output(corpus):
    from src.api.kg.extraction import rejection_diagnostics
    source = load_paper(corpus.paper, corpus.catalogue, corpus.reader)[0][0]
    bad = records()
    bad["observations"][0].update(id="m22", subject_id="secret-unavailable-subject")
    bad["observations"][0]["evidence"] = [dict(quote="secret mismatched provider quote")]
    bad["relationships"] = [dict(id="edge", subject_id="secret-missing-node", object_id="secret-other-node",
        predicate="compares_with", epistemic_status="reported", evidence=[dict(quote=source.text)])]
    details = rejection_diagnostics(CandidateRecords.model_validate(bad), source)
    assert [issue["code"] for issue in details["rejection_issues"]] == [
        "duplicate_record_id", "undeclared_observation_subject", "quote_not_found",
        "undeclared_relationship_endpoint", "undeclared_relationship_endpoint"]
    assert "secret" not in json.dumps(details)


def test_duplicate_id_failure_is_saved_with_specific_reason(corpus, capsys):
    prepare(corpus)
    bad = records()
    bad["observations"][0]["id"] = "m22"
    component, _, client = sdk_component(corpus.settings, [bad])
    try:
        jobs.extract(corpus.directory, corpus.settings, max_calls=1, component=component)
        report = json.loads((corpus.directory / "failures.json").read_text())
        entry = report["failures"][0]
        assert entry["safe_diagnostics"]["rejection_issues"] == [
            dict(code="duplicate_record_id", path="observations.0.id")]
        assert entry["provider_model"] == "gpt-5-mini-test"
        assert entry["response_id"] == "chat-test"
        assert "duplicate_record_id at observations.0.id" in capsys.readouterr().out
    finally:
        client.close()


def test_legacy_generic_failures_remain_readable_and_not_reconstructed(corpus):
    prepare(corpus)
    plan, _ = jobs.read_plan(corpus.directory)
    with jobs.open_checkpoints(corpus.directory, plan) as db:
        point_id = plan["chunks"][0]["point_id"]
        db.execute("UPDATE jobs SET status='failed', attempts=1, error='ExtractionRejected', result=? WHERE id=?",
                   (json.dumps(dict(usage=None, usage_unknown=True)), point_id))
        rows = [dict(row) for row in db.execute("SELECT * FROM jobs")]
        jobs.export(corpus.directory, plan, rows)
    failures = json.loads((corpus.directory / "failures.json").read_text())
    assert failures["failures"][0]["safe_diagnostics"]["rejection_issues"][0]["code"] == "reason_not_recorded"


def test_sampling_option_reuses_existing_plan_and_stops_at_quota(corpus):
    first = prepare(corpus)
    component, requests, client = sdk_component(corpus.settings, [records("M22 has distance 4.27 ± 0.14 kpc.")])
    try:
        result = jobs.extract(corpus.directory, corpus.settings, max_calls=3,
                              chunks_per_paper=1, component=component)
        assert result["model_calls_reserved_this_invocation"] == 1
        assert result["papers_selected_this_invocation"][0]["chunks"] == 1
        assert jobs.read_plan(corpus.directory)[0]["plan_id"] == first["plan_id"]
        result = jobs.extract(corpus.directory, corpus.settings, max_calls=3,
                              chunks_per_paper=1, component=component)
        assert result["model_calls_reserved_this_invocation"] == 0 and len(requests) == 1
    finally:
        client.close()


@pytest.mark.parametrize("options,expected", [
    (["--chunks-per-paper", "3"], dict(chunks_per_paper=3, failed_only=False)),
    (["--failed-only"], dict(chunks_per_paper=None, failed_only=True)),
])
def test_cli_forwards_sampling_and_targeted_retry_without_loading_env(corpus, monkeypatch, options, expected):
    from src.api.kg.__main__ import main
    import src.api.kg.settings as settings_module
    monkeypatch.setattr(settings_module, "KGSettings", lambda: corpus.settings)
    calls = []
    def fake_extract(directory, settings, **kwargs):
        calls.append((directory, settings, kwargs))
        return dict(model_calls=0)
    monkeypatch.setattr(jobs, "extract", fake_extract)
    main(["extract", "--output", str(corpus.directory), "--max-calls", "21", *options])
    assert calls[0][0] == corpus.directory and calls[0][1] is corpus.settings
    assert calls[0][2]["max_calls"] == 21
    assert all(calls[0][2][key] == value for key, value in expected.items())


def test_langfuse_receives_specific_rejection_metadata_without_client_setup(corpus):
    from src.api.kg.tracing import ExtractionTracing
    calls = []
    class Span:
        def update(self, **kwargs):
            calls.append(kwargs)
    diagnostics = dict(rejection_issues=[dict(code="quote_not_found", path="observations.0.evidence.0.quote")])
    tracer = ExtractionTracing(corpus.settings)
    tracer.finish(Span(), dict(usage=None, safe_diagnostics=diagnostics), "ExtractionRejected", 0.5)
    assert calls[0]["metadata"]["safe_diagnostics"] == diagnostics


def test_running_crash_requires_explicit_retry(corpus):
    prepare(corpus)
    plan, _ = jobs.read_plan(corpus.directory)
    with jobs.open_checkpoints(corpus.directory, plan) as db:
        db.execute("UPDATE jobs SET status='running',attempts=1")
    result = jobs.extract(corpus.directory, corpus.settings)
    assert result["states"]["interrupted"] == 3 and result["model_calls_reserved_this_invocation"] == 0


def test_checkpoint_source_tampering_is_rejected(corpus):
    prepare(corpus)
    path = corpus.directory / "plan.json"
    value = json.loads(path.read_text())
    value["chunks"][0]["text"] = "modified"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="integrity"):
        jobs.read_plan(corpus.directory)


def test_directory_single_writer_lock(corpus):
    with jobs.directory_lock(corpus.directory):
        with pytest.raises(ValueError, match="Another KG"):
            with jobs.directory_lock(corpus.directory):
                pass


def test_upload_full_text_identity_not_summary_or_figures(corpus):
    manifest = corpus.row["manifest"]
    corpus.paper["source"] = corpus.row["source"] = "uploads"
    chunks = corpus.reader.read_json(manifest["text"], BUILD, "chunks.json")
    payloads = [dict(id=str(uuid5(NAMESPACE_URL, f"{BUILD}:text:{i}")), payload=dict(
        type="text", chunk_index=i, paper_id=PAPER, build_id=BUILD, source_text=chunk["text"]))
        for i, chunk in enumerate(chunks)]
    payloads.append(dict(id=str(uuid5(NAMESPACE_URL, f"{BUILD}:summary")), payload=dict(type="summary")))
    manifest.update(payloads=corpus.save("payloads.json", payloads),
                    point_ids=[p["id"] for p in payloads], chunk_count=4)
    # Includes previous artifact pointer, as a later Batch manifest can do.
    manifest["artifact"] = corpus.save("manifest.json", manifest)
    loaded, _ = load_paper(corpus.paper, corpus.catalogue, corpus.reader)
    assert len(loaded) == 3
    assert str(loaded[1].point_id) == str(uuid5(NAMESPACE_URL, f"{BUILD}:text:1"))
    payloads[0]["payload"]["source_text"] = "wrong text"
    manifest["payloads"] = corpus.save("payloads.json", payloads)
    manifest["artifact"] = corpus.save("manifest.json", manifest)
    with pytest.raises(ValueError, match="payload identity"):
        load_paper(corpus.paper, corpus.catalogue, corpus.reader)


def test_contiguous_ordinals_required(corpus):
    manifest = corpus.row["manifest"]
    chunks = corpus.reader.read_json(manifest["text"], BUILD, "chunks.json")
    chunks[1]["chunk_index"] = 9
    manifest["text"] = corpus.save("chunks.json", chunks)
    manifest["artifact"] = corpus.save("manifest.json", manifest)
    with pytest.raises(ValueError, match="ordinals"):
        prepare(corpus)


def test_parallel_independent_chunks_are_bounded(corpus):
    prepare(corpus)
    corpus.settings.KG_CONCURRENCY = 2
    barrier, lock = Barrier(2), Lock()
    active, maximum = [0], [0]
    class Component:
        async def run(self, chunk):
            with lock:
                active[0] += 1
                maximum[0] = max(maximum[0], active[0])
            barrier.wait(timeout=5)
            batch = bind_sources(CandidateRecords.model_validate(records(chunk.text)), chunk,
                                 corpus.settings.KG_MODEL)
            with lock:
                active[0] -= 1
            return ScientificResult(batch=batch, graph=staging_graph(batch), usage=None,
                                    provider_model="test", response_id="test")
    result = jobs.extract(corpus.directory, corpus.settings, max_calls=2, component=Component())
    assert result["states"]["complete"] == 2 and maximum[0] == 2
    assert result["attempts_with_unknown_usage"] == 2


def test_validate_detects_candidate_graph_tampering(corpus):
    prepare(corpus)
    component, _, client = sdk_component(corpus.settings, [records()])
    try:
        jobs.extract(corpus.directory, corpus.settings, max_calls=1, component=component)
        with sqlite3.connect(corpus.directory / "checkpoints.sqlite") as db:
            point, value = db.execute("SELECT id,result FROM jobs WHERE status='complete'").fetchone()
            value = json.loads(value)
            value["graph"]["nodes"] = []
            db.execute("UPDATE jobs SET result=? WHERE id=?", (json.dumps(value), point))
        with pytest.raises(ValueError, match="graph differs"):
            jobs.validate(corpus.directory)
    finally:
        client.close()


def test_tracing_errors_never_abort_extraction(corpus, monkeypatch):
    from src.api.kg.tracing import ExtractionTracing
    class BrokenClient:
        def start_observation(self, **kwargs):
            raise RuntimeError("secret details")
        def flush(self):
            raise RuntimeError("secret details")
    tracer = ExtractionTracing(corpus.settings)
    tracer.client = BrokenClient()
    prepare(corpus)
    component, _, client = sdk_component(corpus.settings, [records()])
    try:
        with pytest.warns(UserWarning) as warnings:
            result = jobs.extract(corpus.directory, corpus.settings, max_calls=1,
                                  component=component, tracer=tracer)
        assert result["states"]["complete"] == 1
        assert all("secret details" not in str(w.message) for w in warnings)
    finally:
        client.close()
