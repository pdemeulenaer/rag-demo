"""Offline regressions for Agentic claim grounding and semantic answer coverage."""
import json
from unittest.mock import Mock

import pytest

from src.api.rag.answer_contracts import RAGGenerationResponse
from src.api.rag.modes.agentic.answering import (
    AnswerReview, generate_agentic_answer,
)
from src.api.rag.modes.agentic.contracts import AnswerRequirement


CONTEXTS = [
    {"id": "a", "paper_id": "paper-a", "title": "Paper A", "page": 1,
     "text": "The flow is inward. The mass inflow rate is (1–3) × 10^-3 solar masses/year."},
    {"id": "b", "paper_id": "paper-b", "title": "Paper B", "page": 2,
     "text": "The object has mass 2 solar masses."},
]


def claim(text="The flow is inward.", ids=("a",), needs=()):
    return {"text": text, "cited_context_ids": list(ids), "need_ids": list(needs)}


def draft(*claims):
    return RAGGenerationResponse(claims=list(claims))


def review(supported=(True,), statuses=("satisfied",), indices=None, unplanned=()):
    indices = indices or [[0] for _ in statuses]
    return AnswerReview(
        claims=[{"claim_index": i, "supported": value,
                 "feedback": "" if value else "The cited text does not support this value."}
                for i, value in enumerate(supported)],
        requirements=[{"requirement_id": f"r{i+1}", "status": status,
                       "claim_indices": [] if status == "missing" else indices[i],
                       "feedback": "" if status == "satisfied" else "The numeric value and units are missing."}
                      for i, status in enumerate(statuses)],
        unplanned_requests=list(unplanned),
    )


def run(responses, descriptions=("Report the inflow.",)):
    request = Mock(side_effect=responses)
    result = generate_agentic_answer(
        question="Report the inflow and its rate.",
        requirements=[AnswerRequirement(id=f"r{i+1}", description=value)
                      for i, value in enumerate(descriptions)],
        contexts=CONTEXTS, prompt=[{"role": "user", "content": "Scoped evidence"}],
        request=request,
    )
    return result, request


def test_any_retrieved_chunk_can_support_any_requirement_without_tool_group_membership():
    # The answer's associations need not match whichever search happened to find "a".
    result, request = run([
        draft(claim(needs=("another_search",))),
        review(),
    ])
    assert result.diagnostics["status"] == "complete"
    assert result.response.claims[0].need_ids == ["r1"]
    assert result.response.retrieved_context_ids == ["a"]
    assert request.call_count == 2


def test_tags_and_number_in_evidence_do_not_substitute_for_actual_numeric_answer():
    first = claim(needs=("r1", "r2"))
    corrected = claim("The inflow rate is (1–3) × 10^-3 solar masses/year.")
    result, request = run([
        draft(first),
        review(statuses=("satisfied", "missing")),
        draft(corrected),
        review(supported=(True, True), statuses=("satisfied", "satisfied"),
               indices=[[0], [1]]),
    ], descriptions=("Report the flow direction.", "Report the rate including units and range."))
    assert result.diagnostics["status"] == "complete"
    assert len(result.response.claims) == 2
    assert result.response.claims[0].text == first["text"]
    assert result.response.claims[1].need_ids == ["r2"]
    assert [call.args[2] for call in request.call_args_list] == ["draft", "verify", "repair", "verify"]
    repair = request.call_args_list[2].args[0][-1]["content"]
    assert "Report the rate including units and range." in repair
    assert "approved_claims" in repair
    assert "The numeric value and units are missing." in repair


def test_wrong_unit_conversion_does_not_discard_other_verified_claims():
    result, request = run([
        draft(claim(), claim("The mass is 2 Jupiter masses.", ids=("b",))),
        review(supported=(True, False), statuses=("satisfied", "missing")),
        draft(),
        review(statuses=("satisfied", "missing")),
    ], descriptions=("Report the inflow.", "Report the mass."))
    assert result.diagnostics["status"] == "partial"
    assert [row.text for row in result.response.claims] == ["The flow is inward."]
    assert result.limitations == ["Report the mass."]
    assert result.diagnostics["validation_attempts"][0]["rejected_claims"][0]["code"] == "claim_not_verified"
    assert request.call_count == 4


@pytest.mark.parametrize("ids,code", [
    (("outside-corpus",), "unknown_context_id"),
    (("a", "a"), "duplicate_context_id"),
])
def test_invalid_citation_is_dropped_per_claim_not_per_answer(ids, code):
    result, request = run([
        draft(claim(), claim("Invalid", ids=ids)),
        review(statuses=("satisfied", "missing")),
        RuntimeError("private provider message"),
    ], descriptions=("Report the inflow.", "Report another detail."))
    assert result.response.answer == "The flow is inward."
    assert result.diagnostics["status"] == "partial"
    assert result.diagnostics["validation_attempts"][0]["rejected_claims"][0]["code"] == code
    assert "private provider message" not in json.dumps(result.diagnostics)
    assert request.call_count == 3


def test_verifier_sees_only_each_claims_cited_evidence_no_pooled_or_gold_context():
    _, request = run([draft(claim()), review()])
    payload = json.loads(request.call_args_list[1].args[0][1]["content"])
    assert set(payload) == {"question", "requirements", "claims"}
    assert payload["claims"][0]["cited_evidence"] == [CONTEXTS[0]]
    assert "Paper B" not in json.dumps(payload)
    assert "need_ids" not in payload["claims"][0]


def test_review_failure_during_repair_preserves_previously_verified_claims():
    result, request = run([
        draft(claim()),
        review(statuses=("satisfied", "missing")),
        draft(claim("The mass is 2 solar masses.", ids=("b",))),
        ValueError("invalid review"),
    ], descriptions=("Report the inflow.", "Report the mass."))
    assert result.response.answer == "The flow is inward."
    assert result.limitations == ["Report the mass."]
    assert result.diagnostics["status"] == "partial"
    assert result.diagnostics["validation_attempts"][1]["error_type"] == "ValueError"
    assert request.call_count == 4


@pytest.mark.parametrize("bad_index", [-1, 1, 29])
def test_coverage_cannot_claim_success_using_absent_claim_index(bad_index):
    invalid_review = review(indices=[[bad_index]])
    result, request = run([
        draft(claim()), invalid_review, draft(), invalid_review,
    ])
    assert result.diagnostics["status"] == "partial"
    assert result.diagnostics["requirements"][0]["status"] == "missing"
    assert request.call_count == 4


def test_duplicate_support_assessments_fail_closed():
    bad = review()
    bad.claims.append(bad.claims[0])
    result, request = run([draft(claim()), bad, draft(claim()), bad])
    assert result.response.claims == []
    assert result.diagnostics["status"] == "safe_abstention"
    assert request.call_count == 4


def test_duplicate_requirement_assessments_cannot_claim_complete_answer():
    bad = review()
    bad.requirements.append(bad.requirements[0])
    result, _ = run([draft(claim()), bad, draft(), bad])
    assert result.response.answer == "The flow is inward."
    assert result.diagnostics["status"] == "partial"


def test_all_unverified_claims_abstain_after_one_repair():
    bad = review(supported=(False,))
    result, request = run([draft(claim()), bad, draft(claim()), bad])
    assert result.response.claims == []
    assert result.diagnostics["status"] == "safe_abstention"
    assert request.call_count == 4


def test_requested_detail_omitted_by_planner_is_reported_and_repaired_once():
    incomplete = review(unplanned=("Report the uncertainty.",))
    result, request = run([draft(claim()), incomplete, draft(), incomplete])
    assert result.diagnostics["status"] == "partial"
    assert result.limitations == ["Report the uncertainty."]
    assert request.call_count == 4


def test_malformed_generation_has_only_one_repair_and_no_unverified_output():
    result, request = run([{"claims": [{"text": "missing citations"}]}, RuntimeError("offline")])
    assert result.response.claims == []
    assert result.diagnostics["status"] == "safe_abstention"
    assert request.call_count == 2
    assert [call.args[2] for call in request.call_args_list] == ["draft", "repair"]


def test_repair_cannot_overwrite_a_previously_verified_claim():
    # Even if the second review changes its support assessment of the fixed prefix.
    second = review(supported=(False, True), statuses=("satisfied", "satisfied"), indices=[[0], [1]])
    result, _ = run([
        draft(claim()), review(statuses=("satisfied", "missing")),
        draft(claim("The mass is 2 solar masses.", ids=("b",))), second,
    ], descriptions=("Report the inflow.", "Report the mass."))
    assert result.diagnostics["status"] == "complete"
    assert result.response.claims[0].text == "The flow is inward."
