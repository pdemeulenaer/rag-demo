"""Exercise the installed SDK and serialized HTTP, without network or model calls."""
import json

import httpx
from openai import OpenAI, RateLimitError
from pydantic import BaseModel, ConfigDict, Field, create_model
import pytest

from src.api.core.structured import StructuredOutputError, parse_chat, parse_response


class Fact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str


def chat_body(content='{"value":"supported"}', *, refusal=None, finish="stop"):
    return {"id": "chat-offline", "object": "chat.completion", "created": 0, "model": "gpt-5-mini",
            "choices": [{"index": 0, "finish_reason": finish,
                         "message": {"role": "assistant", "content": content, "refusal": refusal}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13}}


def response_body(content='{"value":"supported"}', *, refusal=False, status="completed"):
    return {"id": "response-offline", "object": "response", "created_at": 0,
            "model": "gpt-5-mini", "status": status,
            "output": [{"id": "message-offline", "type": "message", "role": "assistant",
                        "status": "completed", "content": [
                            {"type": "refusal", "refusal": "Private refusal text"} if refusal else
                            {"type": "output_text", "text": content, "annotations": []}]}],
            "usage": {"input_tokens": 10, "output_tokens": 3, "total_tokens": 13}}


def offline_client(body, status=200):
    calls = []

    def handle(request):
        calls.append(json.loads(request.content))
        return httpx.Response(status, json=body)

    return OpenAI(api_key="offline", max_retries=0,
                  http_client=httpx.Client(transport=httpx.MockTransport(handle))), calls


@pytest.mark.parametrize("endpoint", ["chat", "responses"])
def test_sdk_owns_schema_conversion_and_parsing_including_ref_descriptions(endpoint):
    model = create_model("DescribedFact", nested=(Fact, Field(description="Requested scientific fact.")))
    body = ('{"nested":{"value":"supported"}}')
    client, calls = offline_client(chat_body(body) if endpoint == "chat" else response_body(body))
    with client:
        if endpoint == "chat":
            result, raw = parse_chat(client, model, model="gpt-5-mini", messages=[],
                                     max_completion_tokens=16000, reasoning_effort="low")
            format_spec = calls[0]["response_format"]["json_schema"]
            assert calls[0]["max_completion_tokens"] == 16000
            assert calls[0]["reasoning_effort"] == "low"
        else:
            result, raw = parse_response(client, model, model="gpt-5-mini", input="Question",
                                         max_output_tokens=1200, store=False)
            format_spec = calls[0]["text"]["format"]
            assert calls[0]["max_output_tokens"] == 1200
            assert calls[0]["store"] is False
    assert result.nested.value == "supported"
    assert raw.usage.total_tokens == 13
    assert len(calls) == 1
    assert format_spec["strict"] is True
    nested = format_spec["schema"]["properties"]["nested"]
    assert "$ref" not in nested  # SDK resolves the reference, preserving its description.
    assert nested["description"] == "Requested scientific fact."
    assert nested["required"] == ["value"]
    assert nested["additionalProperties"] is False


@pytest.mark.parametrize("endpoint", ["chat", "responses"])
@pytest.mark.parametrize("content,code", [
    ('{"value":', "json_invalid"), ('{}', "missing"),
    ('{"value":"private text","extra":"private input"}', "extra_forbidden"),
])
def test_invalid_sdk_output_is_safe_and_not_retried(endpoint, content, code):
    client, calls = offline_client(chat_body(content) if endpoint == "chat" else response_body(content))
    with client, pytest.raises(StructuredOutputError) as caught:
        if endpoint == "chat":
            parse_chat(client, Fact, model="gpt-5-mini", messages=[])
        else:
            parse_response(client, Fact, model="gpt-5-mini", input="Private prompt")
    assert caught.value.safe_diagnostics["validation_error_codes"] == [code]
    assert "private" not in str(caught.value.safe_diagnostics).lower()
    assert "Private prompt" not in str(caught.value)
    assert len(calls) == 1


@pytest.mark.parametrize("endpoint", ["chat", "responses"])
def test_refusals_fail_closed_without_retry_or_leaking_refusal_text(endpoint):
    client, calls = offline_client(chat_body(None, refusal="Private refusal text") if endpoint == "chat"
                                   else response_body(refusal=True))
    with client, pytest.raises(StructuredOutputError) as caught:
        if endpoint == "chat":
            parse_chat(client, Fact, model="gpt-5-mini", messages=[])
        else:
            parse_response(client, Fact, model="gpt-5-mini", input="Question")
    assert caught.value.safe_diagnostics["provider_refusal"] is True
    assert caught.value.safe_diagnostics["validation_error_codes"] == ["provider_refusal"]
    assert "Private" not in str(caught.value.safe_diagnostics)
    assert len(calls) == 1


def test_chat_completion_limit_keeps_available_usage_and_finish_diagnostics():
    client, calls = offline_client(chat_body('{"value":', finish="length"))
    with client, pytest.raises(StructuredOutputError) as caught:
        parse_chat(client, Fact, model="gpt-5-mini", messages=[])
    assert caught.value.safe_diagnostics["validation_error_codes"] == ["completion_limit"]
    assert caught.value.safe_diagnostics["provider_finish_reason"] == "length"
    assert caught.value.safe_diagnostics["provider_completion_tokens"] == 3
    assert caught.value.completion.usage.total_tokens == 13
    assert len(calls) == 1


def test_chat_content_filter_is_observable_and_not_retried():
    client, calls = offline_client(chat_body(None, finish="content_filter"))
    with client, pytest.raises(StructuredOutputError) as caught:
        parse_chat(client, Fact, model="gpt-5-mini", messages=[])
    assert caught.value.safe_diagnostics["validation_error_codes"] == ["content_filter"]
    assert len(calls) == 1


def test_incomplete_responses_output_is_not_accepted_even_if_json_is_valid():
    client, calls = offline_client(response_body(status="incomplete"))
    with client, pytest.raises(StructuredOutputError) as caught:
        parse_response(client, Fact, model="gpt-5-mini", input="Question")
    assert caught.value.safe_diagnostics["validation_error_codes"] == ["incomplete_output"]
    assert caught.value.safe_diagnostics["provider_completion_tokens"] == 3
    assert len(calls) == 1


@pytest.mark.parametrize("endpoint", ["chat", "responses"])
def test_transport_errors_do_not_trigger_an_extra_helper_retry(endpoint):
    client, calls = offline_client({"error": {"message": "Private upstream details", "type": "rate_limit"}}, 429)
    with client, pytest.raises(RateLimitError):
        if endpoint == "chat":
            parse_chat(client, Fact, model="gpt-5-mini", messages=[])
        else:
            parse_response(client, Fact, model="gpt-5-mini", input="Question")
    assert len(calls) == 1


@pytest.mark.parametrize("second_valid", [True, False])
def test_native_judge_decimal_pattern_and_bounded_schema_repair(monkeypatch, second_valid):
    from evals import run_benchmark as runner

    schema = runner._reference_judge_schema([("q_original", "Report the measured mass.")])
    monkeypatch.setattr(runner.config, "EVAL_JUDGE_MAX_OUTPUT_TOKENS", 32768)
    calls = []

    def handle(request):
        calls.append(json.loads(request.content))
        numeric_values = ["8"] if len(calls) == 2 and second_valid else ["[]"]
        content = {
            "correctness": 1, "answer_relevance": 1, "abstention": "not_applicable",
            "reason": "Offline schema test.", "answer_checks": {"q_original": [{
                "requested_fact": "Measured mass.", "status": "answered",
                "answer_quotes": ["The mass is 8 solar masses."],
                "required_numeric_values": numeric_values,
                "missing_or_incorrect_detail": "",
                "deficit_basis": "none", "claimed_missing_answer_fragments": [],
            }]},
        }
        return httpx.Response(200, json=response_body(json.dumps(content)))

    client = OpenAI(api_key="offline", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr("src.api.core.clients.openai_client", lambda: client)

    def run():
        return runner._judge_request(
            instructions=runner.REFERENCE_JUDGE_INSTRUCTIONS,
            payload={"actual_answer": "The mass is 8 solar masses."}, schema=schema,
            model="gpt-5-mini", reasoning_effort="minimal",
            answer_for_quotes="The mass is 8 solar masses.")

    with client:
        if second_valid:
            result, metadata = run()
            assert result["answer_checks"]["q_original"][0]["required_numeric_values"] == ["8"]
            failure = metadata["schema_validation_failures"][0]
            assert failure["validation_error_codes"] == ["string_pattern_mismatch"]
            assert metadata["usage"]["usage_incomplete"] is True
            assert metadata["attempts"] == 2
        else:
            with pytest.raises(StructuredOutputError) as caught:
                run()
            assert caught.value.safe_diagnostics["validation_error_codes"] == ["string_pattern_mismatch"]
    assert len(calls) == 2
    assert [row["max_output_tokens"] for row in calls] == [32768, 32768]
    serialized = calls[0]["text"]["format"]["schema"]
    numeric_schema = serialized["$defs"]["ReferenceAnswerCheck"]["properties"]["required_numeric_values"]
    assert numeric_schema["items"]["pattern"] == r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$"
    feedback = json.loads(calls[1]["input"])["structured_format_feedback"]
    assert feedback["validation_error_codes"] == ["string_pattern_mismatch"]
    assert "answer_checks.q_original.0.required_numeric_values.0" in feedback["validation_error_locations"]


@pytest.mark.parametrize("second_explained", [True, False])
def test_native_judge_unexplained_partial_uses_one_repair_without_promoting_score(monkeypatch, second_explained):
    from evals import run_benchmark as runner

    schema = runner._reference_judge_schema([("q_original", "Report mass and its uncertainty.")])
    calls = []

    def handle(request):
        calls.append(json.loads(request.content))
        detail = ("The requested uncertainty is absent although the mass is present."
                  if len(calls) == 2 and second_explained else "")
        payload = {
            "correctness": 1, "answer_relevance": 1, "abstention": "not_applicable",
            "reason": "Offline assessment.", "answer_checks": {"q_original": [{
                "requested_fact": "Mass and uncertainty.", "status": "partial",
                "answer_quotes": ["The mass is 8 solar masses."],
                "required_numeric_values": ["8"], "missing_or_incorrect_detail": detail,
                "deficit_basis": "missing_content", "claimed_missing_answer_fragments": ["uncertainty"],
            }]},
        }
        return httpx.Response(200, json=response_body(json.dumps(payload)))

    client = OpenAI(api_key="offline", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr("src.api.core.clients.openai_client", lambda: client)

    def run():
        return runner._judge_request(
            instructions=runner.REFERENCE_JUDGE_INSTRUCTIONS, payload={"actual_answer": "The mass is 8 solar masses."},
            schema=schema, model="gpt-5-mini", reasoning_effort="minimal",
            answer_for_quotes="The mass is 8 solar masses.")

    with client:
        result, metadata = run()
        result["answer_checks"] = result["answer_checks"]["q_original"]
        adjusted, _ = runner.apply_judge_safeguards(
            {"kind": "single_paper"}, {}, ["point"], result, "The mass is 8 solar masses.")
        assert adjusted["correctness"] == (0.5 if second_explained else None)
        assert metadata["raw_correctness"] == 1
        assert metadata["schema_validation_failures"] == []
        assert metadata["consistency_validation_failures"][0]["checks"][0]["reasons"] == ["non_full_without_deficit"]
    assert len(calls) == 2
    serialized = calls[0]["text"]["format"]["schema"]["$defs"]["ReferenceAnswerCheck"]
    assert "missing_or_incorrect_detail" in serialized["required"]
    assert "missing_or_incorrect_detail" in json.loads(calls[1]["input"])["consistency_feedback"]["instruction"]


@pytest.mark.parametrize("basis,fragments", [
    ("missing_content", ["20% of the half-mass radius"]),
    ("reference_ambiguity", []),
])
@pytest.mark.parametrize("reconciled", [True, False])
def test_native_judge_consistency_repair_is_bounded_and_unresolved_verdicts_remain_visible(
        monkeypatch, basis, fragments, reconciled):
    from evals import run_benchmark as runner

    answer = "Central stars are within 20% of the half-mass radius. The inner radius is 10^-4 pc."
    reference = [
        {"text": "Central stars are within 20% of the half-mass radius."},
        {"text": "Main text: inner radius = 10^-4 pc."},
        {"text": "Figure caption: fiducial inner radius = 10^-4 pc."},
        {"text": "Start of picture text: inner radius = 10 [4] pc. End of picture text."},
    ]
    schema = runner._reference_judge_schema([("q_original", "Report the threshold and inner radius.")])
    calls = []

    def handle(request):
        calls.append(json.loads(request.content))
        fixed = reconciled and len(calls) == 2
        content = {
            "correctness": 1 if fixed else 0.5, "answer_relevance": 1, "abstention": "not_applicable",
            "reason": "Rechecked facts match." if fixed else "The verdict needs reconciliation.",
            "answer_checks": {"q_original": [{
                "requested_fact": "Threshold and inner radius.", "status": "answered" if fixed else "partial",
                "answer_quotes": [answer], "required_numeric_values": ["0.0001"],
                "missing_or_incorrect_detail": "" if fixed else "Threshold absent or radius source ambiguous.",
                "deficit_basis": "none" if fixed else basis,
                "claimed_missing_answer_fragments": [] if fixed else fragments,
            }]},
        }
        body = response_body(json.dumps(content))
        body["id"] = f"response-{len(calls)}"
        return httpx.Response(200, json=body)

    client = OpenAI(api_key="offline", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr("src.api.core.clients.openai_client", lambda: client)
    with client:
        result, metadata = runner._judge_request(
            instructions=runner.REFERENCE_JUDGE_INSTRUCTIONS,
            payload={"actual_answer": answer, "reference_evidence": reference}, schema=schema,
            model="gpt-5-mini", reasoning_effort="minimal", answer_for_quotes=answer)
    assert len(calls) == 2
    assert metadata["attempts"] == 2
    assert metadata["response_ids"] == ["response-1", "response-2"]
    assert metadata["usage"]["input_tokens"] == 20
    assert metadata["usage"]["output_tokens"] == 6
    assert metadata["consistency_status"] == ("no_detected_conflict" if reconciled else "needs_review")
    assert len(metadata["consistency_validation_failures"]) == (1 if reconciled else 2)
    assert metadata["schema_validation_failures"] == []
    assert metadata["quote_validation_failures"] == []
    original = json.loads(calls[0]["input"])
    repaired = json.loads(calls[1]["input"])
    assert original["reference_evidence"] == repaired["reference_evidence"] == reference
    assert original["actual_answer"] == repaired["actual_answer"] == answer
    assert "consistency_feedback" in repaired
    assert "do not automatically" in repaired["consistency_feedback"]["instruction"]
    serialized = calls[0]["text"]["format"]["schema"]["$defs"]["ReferenceAnswerCheck"]
    assert {"deficit_basis", "claimed_missing_answer_fragments"}.issubset(serialized["required"])
    result["answer_checks"] = result["answer_checks"]["q_original"]
    adjusted, _ = runner.apply_judge_safeguards(
        {"kind": "single_paper"}, {}, ["point"], result, answer)
    assert adjusted["correctness"] == (1 if reconciled else None)
    assert metadata["raw_correctness"] == (1 if reconciled else 0.5)
    assert result["reference_score_status"] == ("scored" if reconciled else "unscored_needs_review")


@pytest.mark.parametrize("reconciled", [False, True])
def test_native_answered_with_deficit_preserves_rag_result_and_runs_isolated_grounding(
        monkeypatch, tmp_path, reconciled):
    from contextlib import nullcontext
    from unittest.mock import Mock
    from evals import run_benchmark as runner
    import src.api.rag.retrieval as retrieval

    answer = "The mass is 8 solar masses."
    chunk = {"id": "point-a", "paper_id": "paper-a", "text": answer}
    claim = {"text": answer, "cited_context_ids": ["point-a"], "need_ids": []}
    pipeline = {"answer": answer, "retrieved_chunks": [chunk], "cited_context_ids": ["point-a"],
                "claims": [claim], "execution": {"stop_reason": "sufficient", "actions": []},
                "generation_diagnostics": {"status": "complete", "reason": "verified_answer"}}

    def fake_pipeline(*args, stage_timings, **kwargs):
        stage_timings.update(retrieval_seconds=0.1, generation_seconds=0.2)
        return pipeline

    monkeypatch.setattr(retrieval, "rag_pipeline", fake_pipeline)
    monkeypatch.setattr(runner, "trace_attributes", lambda **kwargs: nullcontext())
    span = Mock()
    monkeypatch.setattr(runner, "observation", lambda **kwargs: nullcontext(span))
    scores = Mock()
    monkeypatch.setattr(runner, "score_trace", scores)
    calls = []

    def handle(request):
        calls.append(json.loads(request.content))
        if len(calls) == 3:
            content = {"groundedness": 1, "reason": "The claim matches its attached cited excerpt."}
        else:
            fixed = reconciled and len(calls) == 2
            content = {"correctness": 1, "answer_relevance": 1, "abstention": "not_applicable",
                       "reason": "Offline fixture.", "answer_checks": {"q_original": [{
                           "requested_fact": "Measured mass.", "status": "answered",
                           "answer_claim_ids": ["a0001"], "required_numeric_values": ["8"],
                           "missing_or_incorrect_detail": "" if fixed else "The unit is missing.",
                           "deficit_basis": "none", "claimed_missing_answer_fragments": [],
                       }]}}
        body = response_body(json.dumps(content))
        body["id"] = f"response-{len(calls)}"
        return httpx.Response(200, json=body)

    client = OpenAI(api_key="offline", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr("src.api.core.clients.openai_client", lambda: client)
    question = {"id": "q1", "kind": "single_paper", "profile": "single_fact",
                "question": "Report the mass.", "reference_answer": answer,
                "paper_ids": ["paper-a"], "reference_evidence": [{"point_id": "point-a", "text": answer}]}
    with client:
        record = runner.evaluate_item(
            question, "agentic", qdrant=Mock(), collection="papers", scope=Mock(), top_k=5,
            generation_model="offline", judge_enabled=True, judge_model="gpt-5-mini",
            judge_reasoning_effort="minimal", run_id="offline", catalogue=Mock())
    assert len(calls) == 3  # Two reference attempts, one independent grounding request.
    assert record["error"] is None
    assert record["answer"] == answer
    assert record["claims"] == [claim]
    assert record["retrieved_chunks"] == [chunk]
    assert record["agent_execution"]["stop_reason"] == "sufficient"
    assert record["generation_diagnostics"]["status"] == "complete"
    assert record["metrics"]["retrieval_recall"] == 1
    assert record["metrics"]["groundedness"] == 1
    assert record["metrics"]["answer_correctness"] == (1 if reconciled else None)
    reference = record["judge_request"]["reference"]
    assert reference["schema_validation_failures"] == []
    assert reference["raw_correctness"] == 1
    assert reference["attempts"] == 2
    assert reference["score_status"] == ("scored" if reconciled else "unscored_needs_review")
    assert reference["consistency_validation_failures"][0]["checks"][0]["reasons"] == ["answered_with_deficit"]
    assert reference["usage"]["total_tokens"] == 26
    assert reference["response_ids"] == ["response-1", "response-2"]
    grounding_payload = json.loads(calls[2]["input"])
    assert "reference_answer" not in grounding_payload
    assert "reference_evidence" not in grounding_payload
    assert grounding_payload["claims"][0]["cited_evidence"][0]["text"] == answer
    assert record["stage_timings"]["judge_grounding_seconds"] >= 0
    assert record["stage_timings"]["retrieval_seconds"] == 0.1
    assert not any(call.args == ("answer_correctness", None) for call in scores.call_args_list)
    if not reconciled:
        assert not any(call.args[0] == "answer_correctness" for call in scores.call_args_list)
    assert span.update.call_args.kwargs["output"]["judge_consistency"]["score_status"] == reference["score_status"]
    runner.write_json(tmp_path / "result.json", record)
    saved = json.loads((tmp_path / "result.json").read_text())
    assert saved["answer"] == answer
    assert saved["metrics"]["answer_correctness"] == (1 if reconciled else None)
    summary = runner.summarize([saved], ["agentic"])["agentic"]
    assert summary["errors"] == 0
    assert summary["metric_sample_counts"]["answer_correctness"] == {"scored": int(reconciled), "unscored": int(not reconciled)}


@pytest.mark.parametrize("first_ids", [["unknown-id"], [], ["a0001", "a0001"]])
def test_native_claim_id_judge_repairs_with_one_shared_retry_and_resolves_original_text(
        monkeypatch, first_ids):
    from evals import run_benchmark as runner

    answer = "The measured method describes cluster structure—unchanged text. " * 12
    claims = [{"text": answer, "cited_context_ids": ["point-a"], "need_ids": []}]
    calls = []

    def handle(request):
        calls.append(json.loads(request.content))
        if len(calls) == 3:
            content = {"groundedness": 1, "reason": "Offline grounding fixture."}
        else:
            content = {"correctness": 1, "answer_relevance": 1, "abstention": "not_applicable",
                       "reason": "Offline fixture, not a copied quote.",
                       "answer_checks": {"q_original": [{
                           "requested_fact": "Describe the method.", "status": "answered",
                           "answer_claim_ids": first_ids if len(calls) == 1 else ["a0001"],
                           "required_numeric_values": [], "missing_or_incorrect_detail": "",
                           "deficit_basis": "none", "claimed_missing_answer_fragments": [],
                       }]}}
        return httpx.Response(200, json=response_body(json.dumps(content)))

    client = OpenAI(api_key="offline", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr("src.api.core.clients.openai_client", lambda: client)
    with client:
        result, metadata = runner.judge(
            {"kind": "single_paper", "question": "Describe the method.",
             "reference_answer": "PRIVATE REFERENCE", "reference_evidence": []},
            answer, [{"id": "point-a", "text": "PRIVATE CITED EVIDENCE"}],
            "gpt-5-mini", "minimal", claims)
    assert len(calls) == 3  # The native SDK adds no retries; one caller-owned repair.
    assert result["correctness"] == 1
    assert result["answer_checks"][0]["answer_claim_ids"] == ["a0001"]
    assert result["answer_checks"][0]["answer_quotes"] == [answer]  # No truncation/rewriting.
    assert result["answer_anchors"][0]["text"] == answer
    assert metadata["reference"]["answer_anchor_mode"] == "claim_ids"
    assert metadata["reference"]["attempts"] == 2
    assert metadata["reference"]["consistency_status"] == "no_detected_conflict"
    if first_ids == ["unknown-id"]:
        assert metadata["reference"]["schema_validation_failures"]
    else:
        assert metadata["reference"]["quote_validation_failures"]
    native_check = calls[0]["text"]["format"]["schema"]["$defs"]["ClaimReferenceCheck"]
    assert "answer_quotes" not in native_check["properties"]
    id_schema = native_check["properties"]["answer_claim_ids"]["items"]
    assert id_schema.get("enum", [id_schema.get("const")]) == ["a0001"]
    assert set(native_check["properties"]) == set(native_check["required"])
    grounding = json.loads(calls[2]["input"])
    assert "answer_anchors" not in grounding
    assert "PRIVATE REFERENCE" not in calls[2]["input"]
    assert grounding["claims"][0]["cited_evidence"][0]["text"] == "PRIVATE CITED EVIDENCE"
    assert "PRIVATE CITED EVIDENCE" not in calls[0]["input"]


@pytest.mark.parametrize("correct_role", [False, True])
def test_method_role_misattribution_remains_a_semantic_error_despite_valid_claim_ids(
        monkeypatch, correct_role):
    """Mocked verdicts test preservation/isolation, not that a live judge detects this error."""
    from evals import run_benchmark as runner

    source = "Gate groups records into a dataset. Link separately finds pairs within that dataset."
    answer = "Link finds pairs." if correct_role else "Gate finds pairs."
    correctness = 1 if correct_role else 0.5
    bodies = [response_body(json.dumps({
        "correctness": correctness, "answer_relevance": 1, "abstention": "not_applicable",
        "reason": "Fixture compares method purpose.", "answer_checks": {"q_original": [{
            "requested_fact": "Identify the method that finds pairs.",
            "status": "answered" if correct_role else "incorrect", "answer_claim_ids": ["a0001"],
            "required_numeric_values": [],
            "missing_or_incorrect_detail": "" if correct_role else "Link, not Gate, finds pairs.",
            "deficit_basis": "none" if correct_role else "incorrect_content",
            "claimed_missing_answer_fragments": [],
        }]}})), response_body(json.dumps({
            "groundedness": correctness, "reason": "Fixture checks pipeline step attribution."}))]
    calls = []

    def handle(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=bodies[len(calls) - 1])

    client = OpenAI(api_key="offline", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr("src.api.core.clients.openai_client", lambda: client)
    with client:
        result, metadata = runner.judge(
            {"kind": "single_paper", "question": "Which method finds pairs?",
             "reference_answer": source, "reference_evidence": []}, answer,
            [{"id": "point", "text": source}], "gpt-5-mini", "minimal",
            [{"text": answer, "cited_context_ids": ["point"], "need_ids": []}])
    assert len(calls) == 2  # Genuine, explained semantic errors do not trigger format repair.
    assert result["correctness"] == correctness
    assert result["groundedness"] == correctness
    assert metadata["reference"]["score_status"] == "scored"
    assert "method's stated purpose" in calls[0]["instructions"]
    assert "Gate finds pairs" in calls[1]["instructions"]
    assert "reference_answer" not in json.loads(calls[1]["input"])


def test_native_effect_schema_keeps_required_fields_and_normalizes_public_coverage():
    from src.api.rag.modes.agentic.answering import _parse_review, _review_schema
    from src.api.rag.modes.agentic.contracts import AnswerRequirement

    schema = _review_schema([AnswerRequirement(id="r1", description="Report mass dependence on distance.")])
    payload = {"claims": [], "unplanned_requests": [], "requirements": {"r1": {
        "status": "missing", "claim_indices": [], "feedback": "Effect not reported.",
        "effect_status": "missing", "effect_claim_indices": [],
    }}}
    client, calls = offline_client(chat_body(json.dumps(payload)))
    with client:
        parsed, _ = parse_chat(client, schema, model="gpt-5-mini", messages=[])
    assert _parse_review(parsed, schema).requirements[0].effect_status == "missing"
    effect = calls[0]["response_format"]["json_schema"]["schema"]["$defs"]["ParameterEffectCoverage"]
    assert {"effect_status", "effect_claim_indices"}.issubset(effect["required"])
    assert effect["additionalProperties"] is False
    assert len(calls) == 1


def test_langfuse_instruments_both_native_parse_endpoints_without_external_services():
    # Isolate Langfuse's SDK monkeypatches from the rest of the offline suite.
    import os
    from pathlib import Path
    import subprocess
    import sys

    script = '''
import json
import httpx
from unittest.mock import Mock
import langfuse.openai as integration
from pydantic import BaseModel
from src.api.core.structured import parse_chat, parse_response

class Fact(BaseModel):
    value: str

tracer = Mock()
span = tracer.start_observation.return_value
span.update.return_value = span
integration.get_client = Mock(return_value=tracer)
calls = []
def handle(request):
    calls.append(request)
    if request.url.path.endswith("chat/completions"):
        body = {"id":"chat-offline","object":"chat.completion","created":0,"model":"gpt-5-mini",
          "choices":[{"index":0,"finish_reason":"stop","message":{"role":"assistant",
            "content":"{\\"value\\":\\"supported\\"}"}}],
          "usage":{"prompt_tokens":10,"completion_tokens":3,"total_tokens":13}}
    else:
        body = {"id":"response-offline","object":"response","created_at":0,"model":"gpt-5-mini",
          "status":"completed","output":[{"id":"message-offline","type":"message",
            "role":"assistant","status":"completed","content":[{"type":"output_text",
              "text":"{\\"value\\":\\"supported\\"}","annotations":[]}]}],
          "usage":{"input_tokens":10,"output_tokens":3,"total_tokens":13}}
    return httpx.Response(200,json=body)

with integration.OpenAI(api_key="offline",max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
    assert parse_chat(client,Fact,model="gpt-5-mini",messages=[])[0].value == "supported"
    assert parse_response(client,Fact,model="gpt-5-mini",input="Question")[0].value == "supported"
assert len(calls) == 2
assert tracer.start_observation.call_count == 2
assert span.end.call_count == 2
assert all(call.kwargs["as_type"] == "generation" for call in tracer.start_observation.call_args_list)
assert all(call.kwargs["usage_details"]["total_tokens"] == 13 for call in span.update.call_args_list)
'''
    repo = Path(__file__).resolve().parents[2]
    result = subprocess.run([sys.executable, "-c", script], cwd="/tmp",
                            env={**os.environ, "PYTHONPATH": str(repo), "LANGFUSE_TRACING_ENABLED": "false"},
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
