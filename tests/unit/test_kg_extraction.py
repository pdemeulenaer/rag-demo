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
from src.api.kg.extraction import PROMPT, PREVIOUS_SCIENTIFIC_REVISION, quarantine_report
from src.api.kg import jobs
from src.api.kg.settings import KGSettings
from src.api.kg.spans import source_spans


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
    evidence = [dict(span_id="s001")]
    return dict(entities=[dict(id="m22", kind="astronomical_object", name="M22", aliases=[], evidence=evidence)],
        observations=[dict(id="distance", subject_id="m22", kind="measurement", statement=text,
            quantity="distance", value_text="3.27", unit_text="kpc", uncertainty_text="± 0.14",
            quantity_dimension="length", quality_flags=[], conditions=[], evidence=evidence)], relationships=[])


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
        for definition in [schema["schema"], *schema["schema"]["$defs"].values()]:
            if definition.get("type") == "object":
                assert definition["additionalProperties"] is False
                assert set(definition["required"]) == set(definition["properties"])
        observation_schema = schema["schema"]["$defs"]["SpanObservation"]
        assert "selection_criterion" in observation_schema["properties"]["kind"]["enum"]
        assert "quality_flags" in observation_schema["required"]
        assert requests[0]["max_completion_tokens"] == 16384
        assert requests[0]["messages"][0] == dict(role="system", content=PROMPT)
        request_input = json.loads(requests[0]["messages"][1]["content"])
        assert request_input["source_spans"] == [dict(span_id="s001", text="M22 has distance 3.27 ± 0.14 kpc.")]
        assert "source_text" not in request_input
        saved = json.loads((corpus.directory / "candidates.json").read_text())
        batch = saved["chunks"][0]["batch"]
        assert batch["entities"][0]["id"].startswith(f"{BUILD}:{REVISION}:")
        assert batch["observations"][0]["uncertainty_text"] == "± 0.14"
        assert saved["chunks"][0]["source_spans"][0]["id"] == "s001"
        assert saved["graph_ready"] is False and saved["review_status"] == "needs_review"
    finally:
        client.close()


def test_invalid_relationship_roles_are_quarantined_by_native_pipeline(corpus):
    prepare(corpus)
    body = records()
    body["entities"].append(dict(id="catalogue", kind="dataset", name="Catalogue",
                                 aliases=[], evidence=[dict(span_id="s001")]))
    body["relationships"] = [dict(id="edge", subject_id="m22", object_id="catalogue",
        predicate="observed_with", epistemic_status="reported", evidence=[dict(span_id="s001")])]
    component, requests, client = sdk_component(corpus.settings, [body])
    try:
        result = jobs.extract(corpus.directory, corpus.settings, max_calls=1, component=component)
        assert result["states"]["complete"] == 1 and len(requests) == 1
        saved = json.loads((corpus.directory / "candidates.json").read_text())["chunks"][0]
        assert saved["quarantine"][0]["reasons"] == ["invalid_relationship_role"]
        assert saved["batch"]["relationships"][0]["object_id"].endswith(":catalogue")
        assert all(edge["type"] != "OBSERVED_WITH" for edge in saved["graph"]["relationships"])
        assert len(saved["graph"]["nodes"]) == 3  # Valid entities/observation survive.
        assert jobs.validate(corpus.directory)["quarantined_records"] == 1
    finally:
        client.close()


@pytest.mark.parametrize("tamper", [None, "quarantine", "graph", "schema"])
def test_numeric_quarantine_preserves_raw_values_and_excludes_dependent_edges(corpus, tamper):
    prepare(corpus)
    body = records()
    ambiguous = deepcopy(body["observations"][0])
    ambiguous.update(id="damaged", quantity="birth rate", value_text="6.91[+0].82",
                     unit_text="Myr", uncertainty_text=None, quantity_dimension="inverse_time")
    body["observations"].append(ambiguous)
    body["relationships"] = [dict(id="edge", subject_id="distance", object_id="damaged",
        predicate="compares_with", epistemic_status="reported", evidence=[dict(span_id="s001")])]
    component, requests, client = sdk_component(corpus.settings, [body])
    try:
        result = jobs.extract(corpus.directory, corpus.settings, max_calls=1, component=component)
        assert result["states"]["complete"] == 1 and result["quarantined_records"] == 2
        saved = json.loads((corpus.directory / "candidates.json").read_text())["chunks"][0]
        bad = saved["batch"]["observations"][1]
        assert bad["value_text"] == "6.91[+0].82" and bad["unit_text"] == "Myr"
        assert bad["quality_flags"] == ["numeric_format_ambiguous", "unit_dimension_conflict"]
        assert bad["evidence"][0]["quote"] == "M22 has distance 3.27 ± 0.14 kpc."
        assert len(saved["graph"]["nodes"]) == 2  # Entity and clean observation survive.
        assert [edge["type"] for edge in saved["graph"]["relationships"]] == ["HAS_OBSERVATION"]
        validated = jobs.validate(corpus.directory)
        assert validated["quarantined_records"] == 2 and validated["semantic_schema_checked_chunks"] == 1
        assert validated["graph_ready"] is False and len(requests) == 1
        if tamper:
            with sqlite3.connect(corpus.directory / "checkpoints.sqlite") as db:
                point, raw = db.execute("SELECT id,result FROM jobs WHERE status='complete'").fetchone()
                raw = json.loads(raw)
                if tamper == "quarantine":
                    raw["quarantine"] = []
                elif tamper == "graph":
                    raw["graph"]["nodes"].append(dict(id=bad["id"], label="Observation", properties={}))
                else:
                    raw["batch"]["schema_version"] = "scientific-kg-v1"
                    for observation in raw["batch"]["observations"]:
                        observation.pop("quantity_dimension")
                        observation.pop("quality_flags")
                db.execute("UPDATE jobs SET result=? WHERE id=?", (json.dumps(raw), point))
            with pytest.raises(ValueError, match="differs|schema/revision"):
                jobs.validate(corpus.directory)
    finally:
        client.close()


@pytest.mark.parametrize("bad", ["unknown_span", "duplicate_id", "refuse", "connection"])
def test_failures_checkpoint_not_silent_retry(corpus, bad):
    prepare(corpus)
    output = records()
    if bad == "unknown_span":
        output["observations"][0]["evidence"] = [dict(span_id="s999")]
    elif bad == "duplicate_id":
        output["observations"][0]["id"] = "m22"
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
            if bad == "duplicate_id":
                assert diagnostics["rejection_issues"][0]["code"] == "duplicate_record_id"
                assert diagnostics["rejection_issues"][0]["path"].startswith("observations.0.")
            if bad == "unknown_span":
                assert diagnostics["validation_error_codes"] == ["literal_error"]
                assert diagnostics["validation_error_locations"] == ["observations.0.evidence.0.span_id"]
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
    bad["observations"][0]["id"] = "m22"
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
    bad["observations"][0]["evidence"] = [dict(span_id="secret unavailable source span")]
    bad["relationships"] = [dict(id="edge", subject_id="secret-missing-node", object_id="secret-other-node",
        predicate="compares_with", epistemic_status="reported", evidence=[dict(span_id="s001")])]
    details = rejection_diagnostics(CandidateRecords.model_validate(bad), source)
    assert [issue["code"] for issue in details["rejection_issues"]] == [
        "duplicate_record_id", "undeclared_observation_subject", "unknown_source_span",
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
                                    provider_model="test", response_id="test", source_spans=source_spans(chunk.text))
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


def test_sdk_schema_limits_span_ids_to_this_chunk(corpus):
    import asyncio
    text = "# Results\n\nM22 has distance 3.27 ± 0.14 kpc.\n\n[Fe∕H] = −1.73 ± 0.17 dex."
    chunk = SourceChunk(paper_id=PAPER, build_id=BUILD, point_id=str(uuid5(NAMESPACE_URL, "span-test")),
                        collection="arxiv_papers_v2", source="arxiv", page_number=1,
                        section_header="Results", text=text)
    body = records()
    for record in body["entities"] + body["observations"]:
        record["evidence"] = [dict(span_id="s002"), dict(span_id="s003")]
    component, requests, client = sdk_component(corpus.settings, [body])
    try:
        result = asyncio.run(component.run(chunk))
        schema = requests[0]["response_format"]["json_schema"]["schema"]
        assert schema["$defs"]["ChunkSpanReference"]["properties"]["span_id"]["enum"] == ["s001", "s002", "s003"]
        assert "quote" not in schema["$defs"]["ChunkSpanReference"]["properties"]
        assert [e.quote for e in result.batch.observations[0].evidence] == [
            "M22 has distance 3.27 ± 0.14 kpc.", "[Fe∕H] = −1.73 ± 0.17 dex."]
        result.batch.validate_sources([chunk])
    finally:
        client.close()


def test_binding_rejects_unknown_span_without_fuzzy_repair(corpus):
    source = load_paper(corpus.paper, corpus.catalogue, corpus.reader)[0][0]
    body = records()
    body["entities"][0]["evidence"] = [dict(span_id="s999")]
    with pytest.raises(ValueError, match="unknown source span"):
        bind_sources(CandidateRecords.model_validate(body), source, corpus.settings.KG_MODEL)


@pytest.mark.parametrize("text,kind,quantity,value,unit", [
    ("Cluster A has distance 4.2 ± 0.3 kpc.", "measurement", "distance", "4.2", "kpc"),
    ("The populations have comparable rotation.", "qualitative_finding", None, None, None),
    ("The populations have near-solar metallicity.", "qualitative_finding", None, None, None),
    ("We simulate a mass grid from 1 to 5 solar masses.", "model_parameter", "mass", "1 to 5", "solar masses"),
    ("The simulation yields a mass of 3 solar masses.", "simulation_result", "mass", "3", "solar masses"),
    ("We select stars brighter than magnitude 18.", "selection_criterion", "magnitude", "18", None),
    ("The measured flux upper limit is 2 mJy.", "upper_limit", "flux", "2", "mJy"),
    ("We adopt radius 2 pc from an earlier study.", "adopted_value", "radius", "2", "pc"),
    ("We assume spherical symmetry.", "assumption", None, None, None),
    ("We will test spherical symmetry.", "planned_analysis", None, None, None),
    ("The caption reports a detected velocity gradient.", "qualitative_finding", None, None, None),
])
def test_prompt_classification_examples_survive_native_parsing_without_retyping(corpus, text, kind, quantity, value, unit):
    """Mocked contract regression, NOT a claim that a live model classifies correctly."""
    import asyncio
    body = records(text)
    body["observations"][0].update(kind=kind, quantity=quantity, value_text=value,
        unit_text=unit, uncertainty_text=None, quantity_dimension=None)
    chunk = SourceChunk(paper_id=PAPER, build_id=BUILD, point_id=str(uuid5(NAMESPACE_URL, text)),
        collection="arxiv_papers_v2", source="arxiv", page_number=1, text=text)
    component, requests, client = sdk_component(corpus.settings, [body])
    try:
        result = asyncio.run(component.run(chunk))
        observation = result.batch.observations[0]
        assert observation.kind == kind and observation.value_text == value
        assert not observation.quarantined and not result.quarantine
        assert observation.evidence[0].quote == text
        assert text.rstrip(".") in requests[0]["messages"][0]["content"]
        assert len(requests) == 1  # Checklist is not a separate reviewer call.
    finally:
        client.close()


def test_presentation_only_chunk_can_return_empty_without_injecting_prompt_examples(corpus):
    import asyncio
    text = "Black circles denote members; ticks are at 0, 1, 2."
    chunk = SourceChunk(paper_id=PAPER, build_id=BUILD, point_id=str(uuid5(NAMESPACE_URL, text)),
        collection="arxiv_papers_v2", source="arxiv", page_number=1, text=text)
    component, requests, client = sdk_component(corpus.settings, [dict(entities=[], observations=[], relationships=[])])
    try:
        result = asyncio.run(component.run(chunk))
        assert result.graph.nodes == [] and result.graph.relationships == []
        source = json.loads(requests[0]["messages"][1]["content"])
        assert source["source_spans"] == [dict(span_id="s001", text=text)]
        assert "Cluster A" not in requests[0]["messages"][1]["content"]
        assert len(requests) == 1
    finally:
        client.close()


def test_prompt_checklist_keeps_guards_and_example_authority_explicit():
    assert "Examples below illustrate classification, NEVER facts to extract" in PROMPT
    assert "Final consistency checklist" in PROMPT
    assert "Every observation.subject_id must name an entity declared in entities" in PROMPT
    assert "Omit unsupported or incompatible relationships" in PROMPT
    assert "Do not complete a dangling sentence" in PROMPT
    assert "No numeric repairs" in PROMPT
    assert "NOT analysis uses_dataset instrument" in PROMPT
    assert "NOT study located_in object" in PROMPT
    assert "Allowed relationship roles" in PROMPT
    # Guidance changed; do not masquerade as the frozen pilot-schema-v3 revision.
    assert REVISION != PREVIOUS_SCIENTIFIC_REVISION


@pytest.mark.parametrize("tamper", [False, True])
@pytest.mark.parametrize("previous_revision", [PREVIOUS_SCIENTIFIC_REVISION,
    "85c8277bd45e9f37ec74d2dd00199020f3ec0f405e1a587b16ef67828b6983f4"])
def test_previous_scientific_revision_preserves_v2_quarantine_and_span_validation(corpus, tamper, previous_revision):
    from src.api.kg.scientific_schema import ExtractionBatch
    prepare(corpus)
    plan, chunks = jobs.read_plan(corpus.directory)
    body = records()
    body["observations"][0]["quality_flags"] = ["ambiguous_source_uncertainty"]
    batch = bind_sources(CandidateRecords.model_validate(body), chunks[0], corpus.settings.KG_MODEL)
    raw = batch.model_dump(mode="json")
    raw["schema_version"] = "scientific-kg-v2"
    raw["extraction_revision"] = previous_revision
    for group in ("entities", "observations", "relationships"):
        for record in raw[group]:
            for key in ("id", "subject_id", "object_id"):
                if key in record:
                    record[key] = record[key].replace(REVISION, previous_revision)
    previous = ExtractionBatch.model_validate(raw)
    result = ScientificResult(batch=previous, graph=staging_graph(previous), usage=None,
        provider_model="old-test", response_id="old-test", source_spans=source_spans(chunks[0].text),
        quarantine=quarantine_report(previous))
    plan["extraction_revision"] = previous_revision
    plan["plan_id"] = sha256(jobs.canonical({k:v for k,v in plan.items() if k != "plan_id"}).encode()).hexdigest()
    (corpus.directory / "plan.json").write_text(jobs.canonical(plan))
    with jobs.open_checkpoints(corpus.directory, plan) as db:
        saved = result.model_dump(mode="json")
        if tamper:
            saved["source_spans"][0]["start"] = 1
        db.execute("UPDATE jobs SET status='complete',attempts=1,result=? WHERE id=?",
                   (json.dumps(saved), str(chunks[0].point_id)))
    if tamper:
        with pytest.raises(ValueError, match="source spans differ"):
            jobs.validate(corpus.directory)
    else:
        report = jobs.validate(corpus.directory)
        assert report["validated_chunks"] == report["semantic_schema_checked_chunks"] == 1
        assert report["legacy_chunks"] == 0 and report["quarantined_records"] == 1
    # Historical results are readable only; current extraction cannot mix revisions.
    with pytest.raises(ValueError, match="legacy extraction schema/revision"):
        jobs.read_plan(corpus.directory)


@pytest.mark.parametrize("previous", [
    "31a420f578c730b5c441afb60c717bdce4b8c647318cad0a2e6c13ad24858bf0",
    "6e228ba2ee5f121e5435aeb2a57a99cad12b4aefdcd6264653275e2dbcc277c8",
])
def test_legacy_quote_plan_readable_for_validation_but_not_extraction(corpus, previous):
    from src.api.kg.extraction import LEGACY_REVISIONS
    prepare(corpus)
    plan, chunks = jobs.read_plan(corpus.directory)
    # Build a representative legacy local checkpoint without API/database services.
    batch = bind_sources(CandidateRecords.model_validate(records()), chunks[0], corpus.settings.KG_MODEL)
    raw = batch.model_dump(mode="json")
    assert previous in LEGACY_REVISIONS
    raw["schema_version"] = "scientific-kg-v1"
    raw["extraction_revision"] = previous
    for record in raw["observations"]:
        record.pop("quantity_dimension")
        record.pop("quality_flags")
    for group in ("entities", "observations", "relationships"):
        for record in raw[group]:
            for key in ("id", "subject_id", "object_id"):
                if key in record:
                    record[key] = record[key].replace(REVISION, previous)
    from src.api.kg.contracts import ExtractionBatch
    old_batch = ExtractionBatch.model_validate(raw)
    result = ScientificResult(batch=old_batch, graph=staging_graph(old_batch), usage=None,
                              provider_model="old-test", response_id="old-test",
                              source_spans=source_spans(chunks[0].text))
    plan["extraction_revision"] = previous
    plan["plan_id"] = sha256(jobs.canonical({k:v for k,v in plan.items() if k != "plan_id"}).encode()).hexdigest()
    (corpus.directory / "plan.json").write_text(jobs.canonical(plan))
    with jobs.open_checkpoints(corpus.directory, plan) as db:
        db.execute("UPDATE jobs SET status='complete',attempts=1,result=? WHERE id=?",
                   (result.model_dump_json(), str(chunks[0].point_id)))
    assert jobs.validate(corpus.directory)["validated_chunks"] == 1
    with pytest.raises(ValueError, match="legacy extraction schema/revision"):
        jobs.read_plan(corpus.directory)
    assert jobs.read_plan(corpus.directory, require_current_revision=False)[0]["plan_id"] == plan["plan_id"]


def test_validate_rejects_source_span_offset_tampering(corpus):
    prepare(corpus)
    component, _, client = sdk_component(corpus.settings, [records()])
    try:
        jobs.extract(corpus.directory, corpus.settings, max_calls=1, component=component)
        with sqlite3.connect(corpus.directory / "checkpoints.sqlite") as db:
            point, value = db.execute("SELECT id,result FROM jobs WHERE status='complete'").fetchone()
            value = json.loads(value)
            value["source_spans"][0]["start"] = 1
            db.execute("UPDATE jobs SET result=? WHERE id=?", (json.dumps(value), point))
        with pytest.raises(ValueError, match="source spans differ"):
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
