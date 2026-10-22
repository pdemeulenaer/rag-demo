"""Real SDK/mock transport and native parallel-tool timing; never use the network."""
from contextvars import copy_context
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import httpx
from openai import APITimeoutError, OpenAI
import pytest
from pydantic import ValidationError

from src.api.observability.stage_timings import (
    collect_stage_timings, measure_stage, record_stage_seconds,
)
from src.api.rag.search import search_points
from tests.unit.test_rag_presets import runtime


def test_timing_failure_is_recorded_and_request_scopes_are_isolated(monkeypatch):
    import src.api.observability.stage_timings as timing
    monkeypatch.setattr(timing, "monotonic", Mock(side_effect=[10.0, 12.0]))
    first, second = {}, {}
    with collect_stage_timings(first):
        with pytest.raises(RuntimeError), measure_stage("embedding_seconds"):
            raise RuntimeError("synthetic failure")
        with collect_stage_timings(second):
            record_stage_seconds("embedding_seconds", 3.0)
        record_stage_seconds("embedding_seconds", 1.0)
    record_stage_seconds("embedding_seconds", 100.0)  # Outside a request: no mutation.
    assert first == {"embedding_seconds": 3.0}
    assert second == {"embedding_seconds": 3.0}


def test_parallel_context_copies_share_a_locked_sum_without_lost_updates():
    timings = {}
    with collect_stage_timings(timings), ThreadPoolExecutor(max_workers=8) as pool:
        jobs = [pool.submit(copy_context().run, record_stage_seconds, "qdrant_seconds", 0.25)
                for _ in range(100)]
        for job in jobs:
            job.result()
    assert timings == {"qdrant_seconds": 25.0}


def test_native_langgraph_tool_node_propagates_timing_context():
    from langchain_core.messages import AIMessage
    from langchain_core.tools import tool
    from langgraph.prebuilt import ToolNode

    @tool
    def probe(value: str) -> str:
        """Record synthetic retrieval work, without any service call."""
        record_stage_seconds("embedding_seconds", 1.0)
        record_stage_seconds("qdrant_seconds", 2.0)
        return value

    state = {"messages": [AIMessage(content="", tool_calls=[
        dict(name="probe", args={"value": "one"}, id="one", type="tool_call"),
        dict(name="probe", args={"value": "two"}, id="two", type="tool_call"),
    ])]}
    timings = {}
    with collect_stage_timings(timings):
        result = ToolNode([probe]).invoke(state, config={"max_concurrency": 2})
    assert len(result["messages"]) == 2
    assert timings == {"embedding_seconds": 2.0, "qdrant_seconds": 4.0}


@pytest.mark.parametrize("mode", ["vanilla", "dense", "sparse", "hybrid"])
@pytest.mark.parametrize("fails", [False, True])
def test_every_qdrant_mode_is_timed_even_on_failure(monkeypatch, mode, fails):
    import src.api.observability.stage_timings as timing
    monkeypatch.setattr(timing, "monotonic", Mock(side_effect=[10.0, 12.0]))
    client = Mock()
    if fails:
        client.query_points.side_effect = TimeoutError("synthetic Qdrant timeout")
    timings = {}
    with collect_stage_timings(timings):
        if fails:
            with pytest.raises(TimeoutError):
                search_points(client, "papers", [1.0], "sample", 5, mode)
        else:
            assert search_points(client, "papers", [1.0], "sample", 5, mode) is client.query_points.return_value
    client.query_points.assert_called_once()
    assert timings == {"qdrant_seconds": 2.0}


def embedding_response():
    return httpx.Response(200, json={"object": "list", "model": "text-embedding-3-small",
        "data": [{"object": "embedding", "index": 0, "embedding": [1.0, 0.0]}],
        "usage": {"prompt_tokens": 2, "total_tokens": 2}})


@pytest.mark.parametrize("retries", [0, 1, 2])
def test_embedding_native_sdk_honors_request_retry_limit_without_mutating_shared_client(
        runtime, monkeypatch, retries):
    retrieval, _ = runtime
    calls = []

    def handle(request):
        calls.append(request)
        if len(calls) <= retries:
            return httpx.Response(503, headers={"retry-after-ms": "1"},
                                  json={"error": {"message": "synthetic retryable failure"}})
        return embedding_response()

    with httpx.Client(transport=httpx.MockTransport(handle)) as transport:
        client = OpenAI(api_key="offline", base_url="https://offline.invalid/v1", http_client=transport,
                        timeout=77.0, max_retries=2)
        monkeypatch.setattr(retrieval, "openai_client", lambda: client)
        monkeypatch.setattr(retrieval.config, "EMBEDDING_TIMEOUT_SECONDS", 9.0)
        monkeypatch.setattr(retrieval.config, "EMBEDDING_MAX_RETRIES", retries)
        timings = {}
        with collect_stage_timings(timings):
            assert retrieval.get_embedding("synthetic text") == [1.0, 0.0]
        assert len(calls) == retries + 1
        assert all(r.extensions["timeout"]["read"] == 9.0 for r in calls)
        assert all(r.extensions["timeout"]["connect"] == 9.0 for r in calls)
        assert client.timeout == 77.0 and client.max_retries == 2
        assert not transport.is_closed
        assert timings["embedding_seconds"] >= 0


def test_embedding_read_timeout_fails_once_and_retains_timing(runtime, monkeypatch):
    retrieval, _ = runtime
    calls = []

    def handle(request):
        calls.append(request)
        raise httpx.ReadTimeout("synthetic timeout", request=request)

    with httpx.Client(transport=httpx.MockTransport(handle)) as transport:
        client = OpenAI(api_key="offline", base_url="https://offline.invalid/v1", http_client=transport)
        monkeypatch.setattr(retrieval, "openai_client", lambda: client)
        monkeypatch.setattr(retrieval.config, "EMBEDDING_MAX_RETRIES", 0)
        timings = {}
        with collect_stage_timings(timings), pytest.raises(APITimeoutError):
            retrieval.get_embedding("synthetic timeout text")
        assert len(calls) == 1
        assert "embedding_seconds" in timings and "qdrant_seconds" not in timings


@pytest.mark.parametrize("name,value", [("EMBEDDING_TIMEOUT_SECONDS", 0),
                                       ("EMBEDDING_TIMEOUT_SECONDS", 301),
                                       ("EMBEDDING_MAX_RETRIES", -1),
                                       ("EMBEDDING_MAX_RETRIES", 3)])
def test_embedding_configuration_limits_are_validated(name, value):
    from src.api.core.config import Config
    with pytest.raises(ValidationError):
        Config(_env_file=None, **{name: value})


def test_embedding_defaults_do_not_require_a_dotenv_change(monkeypatch):
    from src.api.core.config import Config
    monkeypatch.delenv("EMBEDDING_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("EMBEDDING_MAX_RETRIES", raising=False)
    settings = Config(_env_file=None)
    assert settings.EMBEDDING_TIMEOUT_SECONDS == 30.0
    assert settings.EMBEDDING_MAX_RETRIES == 0


def test_embedding_limits_load_from_a_synthetic_dotenv_not_project_secrets(tmp_path, monkeypatch):
    from src.api.core.config import Config
    monkeypatch.delenv("EMBEDDING_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("EMBEDDING_MAX_RETRIES", raising=False)
    synthetic = tmp_path / "embedding-test.env"
    synthetic.write_text("EMBEDDING_TIMEOUT_SECONDS=15\nEMBEDDING_MAX_RETRIES=1\n")
    settings = Config(_env_file=synthetic)
    assert settings.EMBEDDING_TIMEOUT_SECONDS == 15.0
    assert settings.EMBEDDING_MAX_RETRIES == 1


@pytest.mark.parametrize("fails", [False, True])
def test_benchmark_retains_substage_timings_on_success_and_failure(runtime, monkeypatch, fails):
    from evals import run_benchmark as runner
    retrieval, _ = runtime

    def pipeline(*args, **kwargs):
        record_stage_seconds("embedding_seconds", 2.0)
        if fails:
            raise TimeoutError("synthetic retrieval failure")
        record_stage_seconds("qdrant_seconds", 3.0)
        return dict(answer="No indexed evidence.", retrieved_chunks=[], cited_context_ids=[], claims=[])

    monkeypatch.setattr(retrieval, "rag_pipeline", pipeline)
    result = runner.evaluate_item(dict(id="offline", kind="single_paper", question="Question?",
        reference_answer="Reference", reference_evidence=[]), "kg", qdrant=Mock(), collection="papers",
        scope=Mock(), top_k=5, generation_model="offline", judge_enabled=False,
        judge_model="offline", judge_reasoning_effort="minimal", run_id="offline")
    assert result["stage_timings"]["embedding_seconds"] == 2.0
    assert bool(result["error"]) == fails
    assert ("qdrant_seconds" in result["stage_timings"]) is not fails
    summary = runner.summarize([result], ["kg"])
    report = runner.report_markdown(dict(run_id="offline", dataset_hash="hash", modes=["kg"]), summary)
    assert "Retrieval breakdown" in report
    assert "Embedding | Qdrant | Graph" in report
    assert summary["kg"]["stage_timings"]["sample_counts"]["embedding_seconds"] == 1
