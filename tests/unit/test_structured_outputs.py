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
        "essential_claim_indices": [], "missing_details": ["Effect not reported."],
        "effect_status": "missing", "effect_claim_indices": [], "effect_outcomes": [],
    }}}
    client, calls = offline_client(chat_body(json.dumps(payload)))
    with client:
        parsed, _ = parse_chat(client, schema, model="gpt-5-mini", messages=[])
    assert _parse_review(parsed, schema).requirements[0].effect_status == "missing"
    effect = calls[0]["response_format"]["json_schema"]["schema"]["$defs"]["ParameterEffectCoverage"]
    assert {"effect_status", "effect_claim_indices", "effect_outcomes"}.issubset(effect["required"])
    assert effect["additionalProperties"] is False
    assert len(calls) == 1


def test_native_review_requires_typed_method_roles_and_source_operation_quotes():
    from src.api.rag.modes.agentic.answering import _parse_review, _review_schema
    from src.api.rag.modes.agentic.contracts import AnswerRequirement

    schema = _review_schema([AnswerRequirement(id="r1", description="Identify the pairing method.")])
    payload = {"claims": [{"claim_index": 0, "supported": True, "feedback": "",
        "evidence_quotes": [], "method_attributions": [{
            "applicability": "reported_operation", "claim_quote": "Link finds pairs.",
            "method": "Link", "claimed_operation": "finds pairs", "source_operation": "finds pairs",
            "status": "matched", "evidence_quotes": [{"context_id": "point-a", "quote": "Link finds pairs."}],
        }]}], "unplanned_requests": [], "requirements": {"r1": {
            "status": "satisfied", "claim_indices": [0], "feedback": "",
            "essential_claim_indices": [0], "missing_details": []}}}
    client, calls = offline_client(chat_body(json.dumps(payload)))
    with client:
        parsed, _ = parse_chat(client, schema, model="gpt-5-mini", messages=[])
    assert _parse_review(parsed, schema).claims[0].method_attributions[0].source_operation == "finds pairs"
    defs = calls[0]["response_format"]["json_schema"]["schema"]["$defs"]
    assert "method_attributions" in defs["ClaimCheck"]["required"]
    assert set(defs["MethodAttributionCheck"]["properties"]) == set(defs["MethodAttributionCheck"]["required"])
    assert defs["MethodAttributionCheck"]["additionalProperties"] is False
    assert len(calls) == 1


def test_native_essential_coverage_drops_bad_background_without_a_repair_call():
    from src.api.rag.modes.agentic.answering import generate_agentic_answer
    from src.api.rag.modes.agentic.contracts import AnswerRequirement

    calls = []

    def handle(request):
        calls.append(json.loads(request.content))
        content = ({"claims": [
            {"text": "The mass is 8 solar masses.", "cited_context_ids": ["a"], "need_ids": []},
            {"text": "The profile slope is +1.75.", "cited_context_ids": ["b"], "need_ids": []},
        ]} if len(calls) == 1 else {
            "claims": [{"claim_index": index, "supported": True, "feedback": "",
                        "evidence_quotes": [], "method_attributions": []} for index in (0, 1)],
            "unplanned_requests": [], "requirements": {key: {
                "status": "satisfied", "claim_indices": [0, 1], "feedback": "",
                "essential_claim_indices": [0], "missing_details": [],
            } for key in ("r1", "q_original")}})
        return httpx.Response(200, json=chat_body(json.dumps(content)))

    client = OpenAI(api_key="offline", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    stages = []

    def request(messages, schema, stage):
        stages.append(stage)
        return parse_chat(client, schema, model="gpt-5-mini", messages=messages)[0]

    with client:
        result = generate_agentic_answer(
            question="Report the mass.", requirements=[AnswerRequirement(id="r1", description="Report the mass.")],
            contexts=[{"id": "a", "text": "The mass is 8 solar masses."},
                      {"id": "b", "text": "The profile slope is _γ ∼−_ 1 _._ 75."}],
            prompt=[], request=request, reviewer_model="offline")
    assert stages == ["draft", "verify"]
    assert result.diagnostics["status"] == "complete"
    assert result.limitations == []
    assert [row.text for row in result.response.claims] == ["The mass is 8 solar masses."]
    rejection = result.diagnostics["validation_attempts"][0]["rejected_claims"][0]
    assert rejection["numeric_evidence"]["missing_values"] == ["1.75"]
    coverage = calls[1]["response_format"]["json_schema"]["schema"]["$defs"]["CoverageCheck"]
    assert set(coverage["required"]) == set(coverage["properties"])
    assert {"essential_claim_indices", "missing_details"} <= set(coverage["required"])
    assert coverage["properties"]["essential_claim_indices"]["items"]["minimum"] == 0
    assert "PRIVATE GOLD" not in json.dumps(calls)


@pytest.mark.parametrize("audit", [[], [{"applicability": "not_applicable"}], [{
    "applicability": "reported_operation", "claim_quote": "The mass is 8 solar masses.",
    "method": "[]", "claimed_operation": "reports the mass", "source_operation": "",
    "status": "not_established", "evidence_quotes": [],
}]])
def test_native_conditional_review_keeps_supported_numeric_fact_without_extra_repair(audit):
    from src.api.rag.modes.agentic.answering import generate_agentic_answer
    from src.api.rag.modes.agentic.contracts import AnswerRequirement

    calls = []

    def handle(request):
        calls.append(json.loads(request.content))
        content = ({"claims": [{"text": "The mass is 8 solar masses.", "cited_context_ids": ["point-a"],
                                "need_ids": []}]} if len(calls) == 1 else {
            "claims": [{"claim_index": 0, "supported": True, "feedback": "", "method_attributions": audit,
                        "evidence_quotes": [{"context_id": "point-a", "quote": "The mass is 8 solar masses."}]}],
            "unplanned_requests": [], "requirements": {key: {
                "status": "satisfied", "claim_indices": [0], "feedback": "",
                "essential_claim_indices": [0], "missing_details": []} for key in ("r1", "q_original")},
        })
        return httpx.Response(200, json=chat_body(json.dumps(content)))

    client = OpenAI(api_key="offline", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    stages = []

    def request(messages, schema, stage):
        stages.append(stage)
        return parse_chat(client, schema, model="gpt-5-mini", messages=messages)[0]

    with client:
        result = generate_agentic_answer(
            question="Report the mass.", requirements=[AnswerRequirement(id="r1", description="Report the mass.")],
            contexts=[{"id": "point-a", "text": "The mass is 8 solar masses."}],
            prompt=[], request=request, reviewer_model="offline")
    assert result.diagnostics["status"] == "complete"
    assert result.response.claims[0].text == "The mass is 8 solar masses."
    assert stages == ["draft", "verify"]
    assert len(calls) == 2
    schema = calls[1]["response_format"]["json_schema"]["schema"]
    choices = schema["$defs"]["ClaimCheck"]["properties"]["method_attributions"]["items"]["anyOf"]
    assert {row["$ref"] for row in choices} == {
        "#/$defs/MethodAttributionCheck", "#/$defs/NonApplicableMethodCheck"}
    assert schema["$defs"]["NonApplicableMethodCheck"]["required"] == ["applicability"]
    assert set(schema["$defs"]["NonApplicableMethodCheck"]["properties"]) == {"applicability"}


@pytest.mark.parametrize("case", ["matched", "mismatched", "uncited", "fabricated", "unknown_claim"])
def test_native_grounding_method_audit_is_citation_scoped_and_cannot_keep_conflicting_full_score(
        monkeypatch, case):
    """Tests enforcement of declared verdicts/quotes, not live semantic detection accuracy."""
    from evals import run_benchmark as runner

    source = "Gate groups records. Link finds pairs within those records."
    answer = "Link finds pairs." if case != "mismatched" else "Gate finds pairs."
    row = {"answer_claim_id": "a0010" if case == "unknown_claim" else "a0001",
           "applicability": "reported_operation", "claim_quote": answer,
           "method": "Gate" if case == "mismatched" else "Link",
           "claimed_operation": "finds pairs", "source_operation": "groups records" if case == "mismatched" else "finds pairs",
           "status": "mismatched" if case == "mismatched" else "matched",
           "evidence_quotes": [{"context_id": "point-b" if case == "uncited" else "point-a",
                                "quote": "Link finds pairs on the Moon." if case == "fabricated" else source}]}
    calls = []

    def handle(request):
        calls.append(json.loads(request.content))
        content = ({"correctness": 1, "answer_relevance": 1, "abstention": "not_applicable",
                    "reason": "Offline reference fixture.", "answer_checks": {"q_original": [{
                        "requested_fact": "Identify the pairing method.", "status": "answered",
                        "answer_claim_ids": ["a0001"], "required_numeric_values": [],
                        "missing_or_incorrect_detail": "", "deficit_basis": "none",
                        "claimed_missing_answer_fragments": [],
                    }]}} if len(calls) == 1 else {
                        "groundedness": 1, "reason": "Offline fixture with explicit role audit.",
                        "method_attributions": [row]})
        return httpx.Response(200, json=response_body(json.dumps(content)))

    client = OpenAI(api_key="offline", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr("src.api.core.clients.openai_client", lambda: client)
    with client:
        result, metadata = runner.judge(
            {"kind": "single_paper", "question": "Identify the pairing method.",
             "reference_answer": "PRIVATE REFERENCE", "reference_evidence": []}, answer,
            [{"id": "point-a", "text": source}, {"id": "point-b", "text": source}],
            "gpt-5-mini", "minimal", [{"text": answer, "cited_context_ids": ["point-a"], "need_ids": []}])
    malformed = case in {"uncited", "fabricated", "unknown_claim"}
    assert len(calls) == (3 if malformed else 2)  # One shared annotation/schema retry, no semantic retry.
    assert result["groundedness"] == (None if malformed else 1 if case == "matched" else 0.5)
    if case == "unknown_claim":
        assert metadata["grounding"]["score_status"] == "unscored_error"
        assert len(metadata["grounding"]["schema_validation_failures"]) == 2
        assert result["correctness"] == 1
        return
    assert metadata["grounding"]["method_attributions"] == [{**row, "claim_index": 0}]
    assert bool(metadata["grounding"]["method_validation_failures"]) == (case == "mismatched")
    assert bool(metadata["grounding"]["annotation_validation_failures"]) == malformed
    assert metadata["grounding"]["score_status"] == ("unscored_needs_review" if malformed else "scored")
    if case != "matched":
        assert metadata["grounding"]["raw_groundedness"] == 1
    schema = calls[1]["text"]["format"]["schema"]
    assert "method_attributions" in schema["required"]
    assert set(schema["$defs"]["AnchoredGroundingMethod"]["properties"]) == set(
        schema["$defs"]["AnchoredGroundingMethod"]["required"])
    assert "claim_index" not in schema["$defs"]["AnchoredGroundingMethod"]["properties"]
    grounding = json.loads(calls[1]["input"])
    assert "PRIVATE REFERENCE" not in calls[1]["input"]
    assert "reference_evidence" not in grounding
    assert [chunk["point_id"] for chunk in grounding["claims"][0]["cited_evidence"]] == ["point-a"]


@pytest.mark.parametrize("audit", [{"applicability": "not_applicable"}, {"applicability": "proposed_use"}, {
    "applicability": "reported_operation", "claim_quote": "The mass is 8 solar masses.",
    "method": "[]", "claimed_operation": "reports the mass", "source_operation": "",
    "status": "not_established", "evidence_quotes": [],
}])
def test_native_grounding_ignores_irrelevant_method_gates_but_preserves_verdict_and_isolation(monkeypatch, audit):
    from evals import run_benchmark as runner

    row = {"answer_claim_id": "a0001", **audit}
    calls = []

    def handle(request):
        calls.append(json.loads(request.content))
        content = ({"correctness": 1, "answer_relevance": 1, "abstention": "not_applicable",
            "reason": "Offline fixture.", "answer_checks": {"q_original": [{
                "requested_fact": "Report the mass.", "status": "answered", "answer_claim_ids": ["a0001"],
                "required_numeric_values": ["8"], "missing_or_incorrect_detail": "", "deficit_basis": "none",
                "claimed_missing_answer_fragments": []}]}} if len(calls) == 1 else {
                    "groundedness": 1, "reason": "Supported ordinary fact.", "method_attributions": [row]})
        return httpx.Response(200, json=response_body(json.dumps(content)))

    client = OpenAI(api_key="offline", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr("src.api.core.clients.openai_client", lambda: client)
    with client:
        result, metadata = runner.judge(
            {"kind": "single_paper", "question": "Report the mass.", "reference_answer": "PRIVATE GOLD",
             "reference_evidence": []}, "The mass is 8 solar masses.",
            [{"id": "point-a", "text": "The mass is 8 solar masses."}], "gpt-5-mini", "minimal",
            [{"text": "The mass is 8 solar masses.", "cited_context_ids": ["point-a"], "need_ids": []}])
    assert len(calls) == 2
    assert result["groundedness"] == 1
    assert metadata["grounding"]["method_validation_failures"] == []
    assert bool(metadata["grounding"]["method_scope_issues"]) == (audit["applicability"] == "reported_operation")
    assert "PRIVATE GOLD" not in calls[1]["input"]
    branch = calls[1]["text"]["format"]["schema"]["$defs"]["AnchoredGroundingNonApplicable"]
    assert set(branch["required"]) == {"answer_claim_id", "applicability"}


@pytest.mark.parametrize("second", ["corrected", "still_invalid", "schema_invalid"])
def test_native_grounding_annotation_repair_shares_one_schema_retry(monkeypatch, second):
    from evals import run_benchmark as runner
    calls = []
    valid = {"answer_claim_id": "a0001", "applicability": "reported_operation",
             "claim_quote": "Link finds pairs.", "method": "Link", "claimed_operation": "finds pairs",
             "source_operation": "finds pairs", "status": "matched",
             "evidence_quotes": [{"context_id": "point", "quote": "Link finds pairs."}]}

    def handle(request):
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            content = {"correctness": 1, "answer_relevance": 1, "abstention": "not_applicable",
                       "reason": "Offline.", "answer_checks": {"q_original": [{
                           "requested_fact": "Pairing method", "status": "answered", "answer_claim_ids": ["a0001"],
                           "required_numeric_values": [], "missing_or_incorrect_detail": "", "deficit_basis": "none",
                           "claimed_missing_answer_fragments": []}]}}
        elif len(calls) == 3 and second == "schema_invalid":
            content = {"groundedness": 1}  # The annotation retry already consumed the sole allowance.
        else:
            row = valid if len(calls) == 3 and second == "corrected" else {
                **valid, "evidence_quotes": [{"context_id": "point", "quote": "Link finds pairs on the Moon."}]}
            content = {"groundedness": 1, "reason": "Offline.", "method_attributions": [row]}
        return httpx.Response(200, json=response_body(json.dumps(content)))

    client = OpenAI(api_key="offline", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr("src.api.core.clients.openai_client", lambda: client)
    with client:
        result, metadata = runner.judge(
            {"kind": "single_paper", "question": "Which method finds pairs?", "reference_answer": "PRIVATE GOLD",
             "reference_evidence": []}, "Link finds pairs.", [{"id": "point", "text": "Link finds pairs."}],
            "gpt-5-mini", "minimal", [{"text": "Link finds pairs.", "cited_context_ids": ["point"], "need_ids": []}])
    assert len(calls) == 3
    assert "method_annotation_feedback" in json.loads(calls[2]["input"])
    assert all("PRIVATE GOLD" not in call["input"] for call in calls[1:])
    assert result["correctness"] == 1
    assert result["groundedness"] == (1 if second == "corrected" else None)
    meta = metadata["grounding"]
    assert meta["attempts"] == 2
    assert len(meta["annotation_validation_failures"]) == (2 if second == "still_invalid" else 1)
    assert meta["score_status"] == ({"corrected": "scored", "still_invalid": "unscored_needs_review",
                                    "schema_invalid": "unscored_error"}[second])
    assert meta["usage"]["total_tokens"] > 0


@pytest.mark.parametrize("second_id", ["a0002", "a9999"])
def test_native_grounding_ids_bind_actual_claim_and_share_schema_retry(monkeypatch, second_id):
    from evals import run_benchmark as runner
    calls = []
    answer = "Gate groups records. Link finds pairs."
    claims = [{"text": "Gate groups records.", "cited_context_ids": ["gate"], "need_ids": []},
              {"text": "Link finds pairs.", "cited_context_ids": ["link"], "need_ids": []}]

    def handle(request):
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            content = {"correctness": 1, "answer_relevance": 1, "abstention": "not_applicable",
                       "reason": "Offline fixture.", "answer_checks": {"q_original": [{
                           "requested_fact": "Describe the operations.", "status": "answered",
                           "answer_claim_ids": ["a0001", "a0002"], "required_numeric_values": [],
                           "missing_or_incorrect_detail": "", "deficit_basis": "none",
                           "claimed_missing_answer_fragments": []}]}}
        else:
            content = {"groundedness": 1, "reason": "Offline fixture.", "method_attributions": [{
                "answer_claim_id": "a9999" if len(calls) == 2 else second_id,
                "applicability": "reported_operation", "claim_quote": "Link finds pairs.",
                "method": "Link", "claimed_operation": "finds pairs", "source_operation": "finds pairs",
                "status": "matched", "evidence_quotes": [{"context_id": "link", "quote": "Link finds pairs."}]}]}
        return httpx.Response(200, json=response_body(json.dumps(content)))

    client = OpenAI(api_key="offline", max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr("src.api.core.clients.openai_client", lambda: client)
    with client:
        result, metadata = runner.judge({"kind": "single_paper", "question": "Describe both operations.",
            "reference_answer": "PRIVATE GOLD", "reference_evidence": []}, answer,
            [{"id": "gate", "text": "Gate groups records."}, {"id": "link", "text": "Link finds pairs."}],
            "gpt-5-mini", "minimal", claims)
    assert len(calls) == 3
    assert result["correctness"] == 1
    assert result["groundedness"] == (1 if second_id == "a0002" else None)
    meta = metadata["grounding"]
    assert meta["answer_anchor_mode"] == "claim_ids"
    assert len(meta["schema_validation_failures"]) == (1 if second_id == "a0002" else 2)
    if second_id == "a0002":
        assert meta["method_attributions"][0]["claim_index"] == 1
        assert meta["method_attributions"][0]["answer_claim_id"] == "a0002"
    assert "structured_format_feedback" in json.loads(calls[2]["input"])
    branch = calls[1]["text"]["format"]["schema"]["$defs"]["AnchoredGroundingMethod"]
    assert branch["properties"]["answer_claim_id"]["enum"] == ["a0001", "a0002"]
    assert "claim_index" not in branch["properties"]
    for call in calls[1:]:
        payload = json.loads(call["input"])
        assert "PRIVATE GOLD" not in call["input"]
        assert payload["claims"][1]["answer_claim_id"] == "a0002"
        assert [row["point_id"] for row in payload["claims"][1]["cited_evidence"]] == ["link"]


def test_native_grounding_empty_answer_cannot_invent_a_claim_anchor():
    from evals import run_benchmark as runner
    from pydantic import ValidationError
    schema = runner._grounding_judge_schema([])
    assert schema.model_validate({"groundedness": 1, "reason": "No claims.", "method_attributions": []})
    with pytest.raises(ValidationError):
        schema.model_validate({"groundedness": 1, "reason": "Invented.", "method_attributions": [{
            "answer_claim_id": "a0001", "applicability": "not_applicable"}]})


@pytest.mark.parametrize("explicit_numeric_request", [False, True])
def test_native_original_question_not_planner_defines_mandatory_synthesis_scope(explicit_numeric_request):
    from src.api.rag.modes.agentic.answering import generate_agentic_answer
    from src.api.rag.modes.agentic.contracts import AnswerRequirement
    calls, stages = [], []
    text = "Proposal: use companion counts to test the assumed stellar supply, not a demonstrated conversion."
    question = "How could companion counts test the stellar supply assumption?"
    if explicit_numeric_request:
        question += " Calculate the numerical conversion as well."
    assessment = {"status": "partial", "claim_indices": [0], "essential_claim_indices": [0],
                  "missing_details": ["A numerical conversion is missing."], "feedback": "Conversion missing."}

    def handle(request):
        body = json.loads(request.content)
        calls.append(body)
        if len(calls) == 1:
            content = {"claims": [{"text": text, "cited_context_ids": ["a"], "need_ids": []}]}
        elif len(calls) == 3:
            content = {"claims": []}
        else:
            original = assessment if explicit_numeric_request else {
                "status": "satisfied", "claim_indices": [0], "essential_claim_indices": [0],
                "missing_details": [], "feedback": ""}
            content = {"claims": [{"claim_index": 0, "supported": True, "feedback": "",
                "evidence_quotes": [], "method_attributions": []}],
                "requirements": {"r1": assessment, "q_original": original},
                "unplanned_requests": ["A numerical conversion is missing."]}
        return httpx.Response(200, json=chat_body(json.dumps(content)))

    client = OpenAI(api_key="offline", max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handle)))

    def request(messages, schema, stage):
        stages.append(stage)
        return parse_chat(client, schema, model="gpt-5-mini", messages=messages)[0]

    with client:
        result = generate_agentic_answer(question=question,
            requirements=[AnswerRequirement(id="r1", kind="synthesis",
                description="Propose a supply test and calculate the numerical conversion.")],
            contexts=[{"id": "a", "text": "Companion counts constrain stellar populations."}],
            prompt=[], request=request)
    assert result.diagnostics["status"] == ("partial" if explicit_numeric_request else "complete")
    assert stages == (["draft", "verify", "repair", "verify"] if explicit_numeric_request else ["draft", "verify"])
    assert len(result.response.claims) == 1
    assert result.diagnostics["planner_only_gaps"] == ([] if explicit_numeric_request else ["r1"])
    assert bool(result.limitations) == explicit_numeric_request
    payload = json.loads(calls[1]["messages"][-1]["content"])
    assert payload["original_question_requirements"][0]["description"] == question
    assert payload["completeness_authority"] == "original_question_requirements"


@pytest.mark.parametrize("failing_stage", ["reference", "grounding"])
def test_native_judge_connection_failure_keeps_independent_stage_scores(monkeypatch, failing_stage):
    from evals import run_benchmark as runner
    calls = []

    def handle(request):
        body = json.loads(request.content)
        calls.append(body)
        reference = "reference_answer" in json.loads(body["input"])
        if reference == (failing_stage == "reference"):
            raise httpx.RemoteProtocolError("sensitive network details", request=request)
        content = ({"correctness": 1, "answer_relevance": 1, "abstention": "not_applicable",
                    "reason": "Offline.", "answer_checks": {"q_original": [{
                        "requested_fact": "Result", "status": "answered", "answer_claim_ids": ["a0001"],
                        "required_numeric_values": [], "missing_or_incorrect_detail": "", "deficit_basis": "none",
                        "claimed_missing_answer_fragments": []}]}} if reference else
                   {"groundedness": 1, "reason": "Offline.", "method_attributions": []})
        return httpx.Response(200, json=response_body(json.dumps(content)))

    client = OpenAI(api_key="offline", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr("src.api.core.clients.openai_client", lambda: client)
    timings = {}
    with client:
        result, metadata = runner.judge(
            {"kind": "single_paper", "question": "What happened?", "reference_answer": "PRIVATE GOLD",
             "reference_evidence": []}, "A result.", [{"id": "point", "text": "A result."}],
            "gpt-5-mini", "minimal", [{"text": "A result.", "cited_context_ids": ["point"], "need_ids": []}],
            stage_timings=timings)
    assert len(calls) == 2  # No transport retries, and the other isolated judge still runs.
    assert result["correctness"] == (None if failing_stage == "reference" else 1)
    assert result["groundedness"] == (None if failing_stage == "grounding" else 1)
    assert metadata[failing_stage]["score_status"] == "unscored_error"
    assert metadata[failing_stage]["error"]["category"] == "connection_interrupted"
    assert metadata[failing_stage]["attempts"] == 1
    assert metadata[failing_stage]["usage"]["usage_incomplete"] is True
    assert "sensitive network details" not in json.dumps(metadata)
    assert all(timings[name] >= 0 for name in ("judge_reference_seconds", "judge_grounding_seconds"))
    assert "PRIVATE GOLD" not in calls[1]["input"]


def test_native_effect_outcome_fields_use_pydantic_schema_and_actual_answer_anchors():
    from src.api.rag.answer_contracts import RAGClaim
    from src.api.rag.modes.agentic.answering import _review_schema, _parse_review
    from src.api.rag.modes.agentic.contracts import AnswerRequirement
    claims = [RAGClaim(text="Two pressures were tested.", cited_context_ids=["a"], need_ids=[])]
    schema = _review_schema([AnswerRequirement(id="r1", description="Report yield dependence on pressure.")], claims)
    payload = {"claims": [], "unplanned_requests": [], "requirements": {"r1": {
        "status": "partial", "claim_indices": [0], "essential_claim_indices": [0],
        "missing_details": ["The observed yield change."], "feedback": "Only test settings are stated.",
        "effect_status": "test_settings_only", "effect_claim_indices": [0], "effect_outcomes": [{
            "answer_claim_id": "a0001",
            "requested_parameter": "pressure", "answer_parameter_quote": "pressures",
            "answer_outcome_quote": "", "outcome_kind": "settings_only",
            "reports_requested_outcome": False}]}}}
    client, calls = offline_client(chat_body(json.dumps(payload)))
    with client:
        parsed, _ = parse_chat(client, schema, model="gpt-5-mini", messages=[])
    audit = _parse_review(parsed, schema, claims).requirements[0].effect_outcomes[0]
    assert audit.reports_requested_outcome is False
    assert audit.answer_text == claims[0].text
    assert audit.claim_index == 0
    defs = calls[0]["response_format"]["json_schema"]["schema"]["$defs"]
    assert set(defs["AnchoredEffectOutcome"]["required"]) == {
        "answer_claim_id", "reports_requested_outcome", "requested_parameter",
        "answer_parameter_quote", "answer_outcome_quote", "outcome_kind"}
    assert defs["AnswerClaimId"]["enum"] == ["a0001"]
    assert "effect_outcomes" in defs["ParameterEffectCoverage"]["required"]


def test_native_method_annotation_correction_does_not_generate_another_answer():
    from src.api.rag.modes.agentic.answering import generate_agentic_answer
    from src.api.rag.modes.agentic.contracts import AnswerRequirement

    text = "Link identifies connected pairs."
    source = "Using Link, the analysis identifies connected pairs."
    coverage = {"status": "satisfied", "claim_indices": [0], "essential_claim_indices": [0],
                "missing_details": [], "feedback": ""}
    calls, stages = [], []

    def handle(request):
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            content = {"claims": [{"text": text, "cited_context_ids": ["a"], "need_ids": []}]}
        else:
            content = {"claims": [{"claim_index": 0, "supported": True, "feedback": "",
                "evidence_quotes": [], "method_attributions": [{"applicability": "reported_operation",
                    "claim_quote": source if len(calls) == 2 else text, "method": "Link",
                    "claimed_operation": "identifies connected pairs", "source_operation": "identifies connected pairs",
                    "status": "matched", "evidence_quotes": [{"context_id": "a",
                        "quote": source + " on the Moon" if len(calls) == 2 else source}]}]}],
                "requirements": {"r1": coverage, "q_original": coverage}, "unplanned_requests": []}
        return httpx.Response(200, json=chat_body(json.dumps(content)))

    client = OpenAI(api_key="offline", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    def request(messages, schema, stage):
        stages.append(stage)
        return parse_chat(client, schema, model="gpt-5-mini", messages=messages)[0]
    with client:
        result = generate_agentic_answer(question="Which operation does Link perform?",
            requirements=[AnswerRequirement(id="r1", description="Describe Link's operation.")],
            contexts=[{"id": "a", "text": source}], prompt=[], request=request, reviewer_model="offline")
    assert stages == ["draft", "verify", "verify"]
    assert result.diagnostics["status"] == "complete"
    assert result.response.answer == text
    assert result.diagnostics["annotation_correction_attempts"] == 1
    first, second = [json.loads(call["messages"][-1]["content"]) for call in calls[1:]]
    assert first["answer_anchors"] == second["answer_anchors"]
    assert second["annotation_feedback"]["failures"][0]["code"] == "invalid_method_annotation"


def test_native_frozen_parameter_enum_cannot_be_reassigned_to_measured_outcome():
    from src.api.rag.modes.agentic.answering import _parse_review, _review_schema
    from src.api.rag.modes.agentic.contracts import AnswerRequirement
    from src.api.rag.answer_contracts import RAGClaim
    claims = [RAGClaim(text="As outer radius increases, flux decreases.", cited_context_ids=["a"], need_ids=[])]
    schema = _review_schema([AnswerRequirement(id="r2", description="Report flux sensitivity to outer radius.",
                                              effect_parameters=["outer radius"])], claims)
    payload = {"claims": [{"claim_index": 0, "supported": True, "feedback": "",
        "evidence_quotes": [], "method_attributions": []}], "unplanned_requests": [], "requirements": {"r2": {
        "status": "satisfied", "claim_indices": [0], "essential_claim_indices": [0],
        "missing_details": [], "feedback": "", "effect_status": "reported_effect", "effect_claim_indices": [0],
        "effect_outcomes": [{"answer_claim_id": "a0001", "requested_parameter": "outer radius",
            "answer_parameter_quote": "outer radius", "answer_outcome_quote": "flux decreases",
            "outcome_kind": "reported_change", "reports_requested_outcome": True}]}}}
    client, calls = offline_client(chat_body(json.dumps(payload)))
    with client:
        parsed, _ = parse_chat(client, schema, model="gpt-5-mini", messages=[])
    assert _parse_review(parsed, schema, claims).requirements[0].effect_outcomes[0].requested_parameter == "outer radius"
    wire = calls[0]["response_format"]["json_schema"]["schema"]
    parameter_schema = wire["$defs"]["BoundEffectOutcome_r2"]["properties"]["requested_parameter"]
    assert parameter_schema.get("const", parameter_schema.get("enum")) in ("outer radius", ["outer radius"])
    payload["requirements"]["r2"]["effect_outcomes"][0]["requested_parameter"] = "flux"
    client, invalid_calls = offline_client(chat_body(json.dumps(payload)))
    with client, pytest.raises(StructuredOutputError):
        parse_chat(client, schema, model="gpt-5-mini", messages=[])
    assert len(invalid_calls) == 1  # No hidden SDK retry.


def test_generation_binds_original_question_effect_to_declared_parameter_without_extra_calls():
    from src.api.rag.modes.agentic.answering import generate_agentic_answer
    from src.api.rag.modes.agentic.contracts import AnswerRequirement
    text = "The baseline rate is 2 events per year. As pressure increases, the rate decreases."
    calls, stages = [], []
    def handle(request):
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            content = {"claims": [{"text": text, "cited_context_ids": ["a"], "need_ids": []}]}
        else:
            payload = json.loads(calls[-1]["messages"][-1]["content"])
            assert payload["original_question_requirements"][0]["effect_parameters"] == ["pressure"]
            checks = {}
            for key in ("r1", "r2", "q_original"):
                checks[key] = {"status": "satisfied", "claim_indices": [0], "essential_claim_indices": [0],
                               "missing_details": [], "feedback": ""}
                if key != "r1":
                    checks[key].update(effect_status="reported_effect", effect_claim_indices=[0], effect_outcomes=[{
                        "answer_claim_id": "a0001", "requested_parameter": "pressure",
                        "answer_parameter_quote": "pressure", "answer_outcome_quote": "the rate decreases",
                        "outcome_kind": "reported_change", "reports_requested_outcome": True}])
            content = {"claims": [{"claim_index": 0, "supported": True, "feedback": "", "evidence_quotes": [],
                                    "method_attributions": []}], "requirements": checks, "unplanned_requests": []}
        return httpx.Response(200, json=chat_body(json.dumps(content)))
    client = OpenAI(api_key="offline", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    def request(messages, schema, stage):
        stages.append(stage)
        return parse_chat(client, schema, model="gpt-5-mini", messages=messages)[0]
    with client:
        result = generate_agentic_answer(question="Report the baseline rate and its sensitivity to pressure.",
            requirements=[AnswerRequirement(id="r1", description="Report the baseline rate."),
                          AnswerRequirement(id="r2", description="Report rate sensitivity to pressure.",
                                            effect_parameters=["pressure"])],
            contexts=[{"id": "a", "text": text}], prompt=[], request=request, reviewer_model="offline")
    assert result.diagnostics["status"] == "complete"
    assert stages == ["draft", "verify"]
    native = calls[1]["response_format"]["json_schema"]["schema"]
    assert native["$defs"]["BoundEffectOutcome_q_original"]["properties"]["requested_parameter"]["const"] == "pressure"


def test_grounding_named_method_cannot_bypass_role_audit_with_not_applicable():
    from evals import run_benchmark as runner
    claim = {"text": "The Gate algorithm finds pairs.", "cited_context_ids": ["a"], "need_ids": []}
    invalid, defects, _ = runner._grounding_audit({"groundedness": 1, "reason": "Claimed support.",
        "method_attributions": [{"claim_index": 0, "applicability": "not_applicable"}]},
        [claim], {"a": {"text": "The Gate algorithm selects members. A separate routine finds pairs."}})
    assert invalid == [{"claim_index": 0, "code": "missing_reported_method_audit"}]
    assert defects == []  # An omitted audit is not a fabricated semantic verdict.


@pytest.mark.parametrize("audit", [[], [{"applicability": "not_applicable"}], [{"applicability": "proposed_use"}]])
def test_native_named_algorithm_cannot_waive_role_and_repairs_within_existing_calls(audit):
    from src.api.rag.modes.agentic.answering import generate_agentic_answer
    from src.api.rag.modes.agentic.contracts import AnswerRequirement
    bad = "The Gate algorithm finds linked pairs."
    good = "The Gate algorithm selects members."
    source = "The Gate algorithm selects members. A separate unnamed routine finds linked pairs."
    stages, calls = [], []
    coverage = {"status": "satisfied", "claim_indices": [0], "essential_claim_indices": [0],
                "missing_details": [], "feedback": ""}
    def handle(request):
        calls.append(json.loads(request.content))
        count = len(calls)
        content = ({"claims": [{"text": bad if count == 1 else good,
            "cited_context_ids": ["a"], "need_ids": []}]} if count in (1, 3) else {
            "claims": [{"claim_index": 0, "supported": True, "feedback": "", "evidence_quotes": [],
                "method_attributions": audit if count == 2 else [{"applicability": "reported_operation",
                    "claim_quote": source, "method": "Gate", "claimed_operation": "selects members",
                    "source_operation": "selects members", "status": "matched",
                    "evidence_quotes": [{"context_id": "a", "quote": "The Gate algorithm selects members."}]}]}],
            "requirements": {"r1": coverage, "q_original": coverage}, "unplanned_requests": []})
        return httpx.Response(200, json=chat_body(json.dumps(content)))
    client = OpenAI(api_key="offline", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    def request(messages, schema, stage):
        stages.append(stage)
        return parse_chat(client, schema, model="gpt-5-mini", messages=messages)[0]
    with client:
        result = generate_agentic_answer(question="What operation does Gate perform?",
            requirements=[AnswerRequirement(id="r1", description="Describe Gate's operation.")],
            contexts=[{"id": "a", "text": source}], prompt=[], request=request, reviewer_model="offline")
    assert stages == ["draft", "verify", "repair", "verify"]
    assert result.response.answer == good and result.diagnostics["status"] == "complete"
    assert result.diagnostics["validation_attempts"][0]["rejected_claims"][0]["code"] == "missing_reported_method_audit"
    assert json.loads(calls[1]["messages"][-1]["content"])["claims"][0]["reported_methods_to_audit"] == ["Gate"]
    final_audit = result.diagnostics["validation_attempts"][1]["method_attributions"][0]["checks"][0]
    assert final_audit["claim_quote"] == good  # Source copying cannot change the answer anchor.


def test_native_agentic_outcome_gate_uses_existing_repair_and_preserves_verified_claim():
    from src.api.rag.modes.agentic.answering import generate_agentic_answer
    from src.api.rag.modes.agentic.contracts import AnswerRequirement
    calls, stages = [], []
    setting = "Two pressures were tested."
    outcome = "The yield decreases as pressure increases."

    def handle(request):
        calls.append(json.loads(request.content))
        if len(calls) in (1, 3):
            content = {"claims": [{"text": setting if len(calls) == 1 else outcome,
                                   "cited_context_ids": ["a"], "need_ids": []}]}
        else:
            final = len(calls) == 4
            index = 1 if final else 0
            coverage = {"status": "satisfied", "claim_indices": list(range(index + 1)),
                        "essential_claim_indices": [index], "missing_details": [], "feedback": "",
                        "effect_status": "reported_effect", "effect_claim_indices": [index],
                        "effect_outcomes": [{"answer_claim_id": f"a{index + 1:04d}",
                            "requested_parameter": "pressure", "answer_parameter_quote": "pressure" if final else "pressures",
                            "answer_outcome_quote": "yield decreases" if final else "",
                            "outcome_kind": "reported_change" if final else "settings_only",
                            "reports_requested_outcome": final}]}
            content = {"claims": [{"claim_index": i, "supported": True, "feedback": "",
                                   "evidence_quotes": [], "method_attributions": []} for i in range(index + 1)],
                       "unplanned_requests": [], "requirements": {"r1": coverage, "q_original": coverage}}
        return httpx.Response(200, json=chat_body(json.dumps(content)))

    client = OpenAI(api_key="offline", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handle)))

    def request(messages, schema, stage):
        stages.append(stage)
        parsed, _ = parse_chat(client, schema, model="gpt-5-mini", messages=messages)
        return parsed

    with client:
        result = generate_agentic_answer(
            question="Report yield sensitivity to pressure.",
            requirements=[AnswerRequirement(id="r1", description="Report yield sensitivity to pressure.")],
            contexts=[{"id": "a", "text": setting + " " + outcome}], prompt=[], request=request,
            reviewer_model="offline")
    assert stages == ["draft", "verify", "repair", "verify"]
    assert len(calls) == 4
    assert result.diagnostics["validation_attempts"][0]["requirements"][0]["status"] == "partial"
    assert result.diagnostics["status"] == "complete"
    assert [claim.text for claim in result.response.claims] == [setting, outcome]
    for index in (1, 3):
        defs = calls[index]["response_format"]["json_schema"]["schema"]["$defs"]
        assert "effect_outcomes" in defs["ParameterEffectCoverage"]["required"]


@pytest.mark.parametrize("text,source", [
    ("The measured yield falls slightly when pressure increases.",
     "Increasing the applied pressure leads to a small decrease in yield."),
    ("The measured yield is unchanged when pressure varies.",
     "No change in yield was observed across the tested pressures."),
])
def test_native_answer_anchors_resolve_paraphrases_without_quote_copying_or_repair(text, source):
    from src.api.rag.modes.agentic.answering import generate_agentic_answer
    from src.api.rag.modes.agentic.contracts import AnswerRequirement

    calls, stages = [], []
    coverage = {"status": "satisfied", "claim_indices": [0], "essential_claim_indices": [0],
                "missing_details": [], "feedback": "", "effect_status": "reported_effect",
                "effect_claim_indices": [0], "effect_outcomes": [{
                    "requested_parameter": "pressure", "answer_parameter_quote": "pressure",
                    "answer_outcome_quote": "yield is unchanged" if "unchanged" in text else "yield falls slightly",
                    "outcome_kind": "reported_no_change" if "unchanged" in text else "reported_change",
                    "answer_claim_id": "a0001", "reports_requested_outcome": True}]}
    bodies = [chat_body(json.dumps({"claims": [{
        "text": text, "cited_context_ids": ["a"], "need_ids": []}]})),
        chat_body(json.dumps({"claims": [{"claim_index": 0, "supported": True,
            "feedback": "", "evidence_quotes": [], "method_attributions": []}],
            "requirements": {"r1": coverage, "q_original": coverage}, "unplanned_requests": []}))]

    def handle(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=bodies[len(calls) - 1])

    client = OpenAI(api_key="offline", max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handle)))

    def request(messages, schema, stage):
        stages.append(stage)
        return parse_chat(client, schema, model="gpt-5-mini", messages=messages)[0]

    with client:
        result = generate_agentic_answer(
            question="Report yield dependence on pressure.",
            requirements=[AnswerRequirement(id="r1", description="Report yield dependence on pressure.")],
            contexts=[{"id": "a", "text": source}], prompt=[], request=request,
            reviewer_model="offline")
    assert stages == ["draft", "verify"]
    assert result.diagnostics["status"] == "complete"
    assert result.limitations == []
    assert result.response.claims[0].text == text
    audit = result.diagnostics["requirements"][0]["effect_outcomes"][0]
    assert {key: audit[key] for key in ("answer_claim_id", "claim_index", "answer_text", "reports_requested_outcome")} == {
        "answer_claim_id": "a0001", "claim_index": 0,
        "answer_text": text, "reports_requested_outcome": True}
    assert audit["requested_parameter"] == "pressure"
    assert audit["answer_text"] != source
    payload = json.loads(calls[1]["messages"][-1]["content"])
    assert payload["answer_anchors"] == {"a0001": {"claim_index": 0, "text": text}}
    assert payload["claims"][0]["answer_claim_id"] == "a0001"
    assert "text" not in payload["claims"][0]  # Do not duplicate answer text in the input.
    assert payload["claims"][0]["cited_evidence"][0]["text"] == source
    assert "PRIVATE GOLD" not in json.dumps(calls)
    assert result.diagnostics["annotation_correction_attempts"] == 0


@pytest.mark.parametrize("bad_audit", [
    {"answer_claim_id": "a9999", "reports_requested_outcome": True},
    {"answer_claim_id": "source-a", "reports_requested_outcome": True},
    {"claim_index": 0, "parameter_quote": "applied pressure",
     "outcome_quote": "leads to a small decrease", "reports_requested_outcome": True},
    {"answer_claim_id": "a0001", "answer_text": "Source-only result", "reports_requested_outcome": True},
])
@pytest.mark.parametrize("corrected", [True, False])
def test_native_invalid_effect_annotation_reuses_second_review_without_redrafting(bad_audit, corrected):
    from src.api.rag.modes.agentic.answering import generate_agentic_answer
    from src.api.rag.modes.agentic.contracts import AnswerRequirement

    text = "The yield decreases when pressure increases."
    calls, stages = [], []

    def handle(request):
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            content = {"claims": [{"text": text, "cited_context_ids": ["a"], "need_ids": []}]}
        else:
            audit = ({"answer_claim_id": "a0001", "reports_requested_outcome": True,
                      "requested_parameter": "pressure", "answer_parameter_quote": "pressure",
                      "answer_outcome_quote": "yield decreases", "outcome_kind": "reported_change"}
                     if len(calls) == 3 and corrected else bad_audit)
            coverage = {"status": "satisfied", "claim_indices": [0], "essential_claim_indices": [0],
                "missing_details": [], "feedback": "", "effect_status": "reported_effect",
                "effect_claim_indices": [0], "effect_outcomes": [audit]}
            content = {"claims": [{"claim_index": 0, "supported": True, "feedback": "",
                "evidence_quotes": [], "method_attributions": []}], "unplanned_requests": [],
                "requirements": {"r1": coverage, "q_original": coverage}}
        return httpx.Response(200, json=chat_body(json.dumps(content)))

    client = OpenAI(api_key="offline", max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handle)))

    def request(messages, schema, stage):
        stages.append(stage)
        return parse_chat(client, schema, model="gpt-5-mini", messages=messages)[0]

    with client:
        result = generate_agentic_answer(
            question="Report yield sensitivity to pressure.",
            requirements=[AnswerRequirement(id="r1", description="Report yield sensitivity to pressure.")],
            contexts=[{"id": "a", "text": text}], prompt=[], request=request,
            reviewer_model="offline")
    assert stages == ["draft", "verify", "verify"]
    assert len(calls) == 3
    first, second = [json.loads(call["messages"][-1]["content"]) for call in calls[1:]]
    assert first["answer_anchors"] == second["answer_anchors"]
    assert first["claims"] == second["claims"]
    assert "annotation_feedback" in second
    assert "promote a verdict automatically" in second["annotation_feedback"]["instruction"]
    assert result.diagnostics["annotation_correction_attempts"] == 1
    assert "repair_seconds" not in result.diagnostics["stage_timings"]
    assert result.diagnostics["validation_attempts"][0]["failed_stage"] == "verify"
    assert result.diagnostics["status"] == ("complete" if corrected else "safe_abstention")
    if corrected:
        assert result.response.claims[0].text == text
        assert result.limitations == []
    else:
        assert result.response.claims == []  # Neither malformed audit may approve output.


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
