import json
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from evals import run_benchmark as runner
from evals import review_dataset as review


def reviewed_dataset(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "schema_version": 1, "source": "arxiv", "corpus_fingerprint": "corpus-1",
        "active_build_ids": ["build-1"],
        "papers": [{"collection": "papers", "embedding_model": runner.config.EMBEDDING_MODEL}],
    }
    reviewed = {
        "schema_version": 1, "snapshot_hash": runner.canonical_hash(snapshot), "plan_hash": "plan",
        "questions": [
            {"id": "q1", "kind": "single_paper", "profile": "single_fact",
             "question": "What happened?",
             "reference_answer": "A result.", "review_status": "approved",
             "reference_evidence": [{"point_id": "gold-1"}]},
            {"id": "q2", "kind": "single_paper", "question": "Rejected?",
             "reference_answer": "No.", "review_status": "rejected", "reference_evidence": []},
        ],
    }
    (tmp_path / "snapshot.json").write_text(json.dumps(snapshot))
    path = tmp_path / "questions.reviewed.json"
    path.write_text(json.dumps(reviewed))
    return path


def test_load_reviewed_keeps_only_approved_and_validates_snapshot(tmp_path):
    path = reviewed_dataset(tmp_path)
    _, snapshot, questions, dataset_hash = runner.load_reviewed(path)
    assert snapshot["corpus_fingerprint"] == "corpus-1"
    assert [row["id"] for row in questions] == ["q1"]
    assert len(dataset_hash) == 64


def test_load_reviewed_filters_schema_v2_split(tmp_path):
    snapshot = {
        "schema_version": 1,
        "corpus_fingerprint": "corpus-2",
        "active_build_ids": ["build-1", "build-2"],
        "papers": [
            {"paper_id": "paper-1", "build_id": "build-1", "collection": "papers",
             "embedding_model": runner.config.EMBEDDING_MODEL},
            {"paper_id": "paper-2", "build_id": "build-2", "collection": "papers",
             "embedding_model": runner.config.EMBEDDING_MODEL},
        ],
        "evidence": [],
    }
    questions = []
    for number in (1, 2):
        questions.append({
            "id": f"q{number}", "kind": "single_paper", "question": f"Question {number}?",
            "reference_answer": "Answer.", "review_status": "approved",
            "answerability_scope": "supplied_excerpts_only",
            "reference_evidence": [{"point_id": f"point-{number}",
                                    "paper_id": f"paper-{number}",
                                    "build_id": f"build-{number}"}],
            "paper_ids": [f"paper-{number}"],
            "review": {"reviewer": "reviewer", "reviewed_at": "2026-09-15T12:00:00Z",
                       "decision": "approved", "original_sources_checked": True},
        })
    reviewed = {"schema_version": 2, "snapshot_hash": runner.canonical_hash(snapshot),
                "plan_hash": "plan", "questions": questions}
    reviewed = review.assign_splits(reviewed, snapshot, test_ratio=0.5, seed=42)
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "snapshot.json").write_text(json.dumps(snapshot))
    path = tmp_path / "questions.split.json"
    path.write_text(json.dumps(reviewed))

    _, _, selected, _ = runner.load_reviewed(path, "test")
    assert len(selected) == 1
    assert selected[0]["split"] == "test"


def test_schema_v1_cannot_claim_a_held_out_split(tmp_path):
    path = reviewed_dataset(tmp_path)
    with pytest.raises(runner.BenchmarkError, match="do not define"):
        runner.load_reviewed(path, "test")


def test_deterministic_metrics_uses_qdrant_point_ids():
    metrics = runner.deterministic_metrics(
        {"paper_ids": ["paper-1", "paper-2"],
         "reference_evidence": [{"point_id": "gold"}, {"point_id": "missed"}]},
        [{"id": "gold", "paper_id": "paper-1"},
         {"id": "other", "paper_id": "distractor"}], ["gold"])
    assert metrics["retrieval_hit"] == 1.0
    assert metrics["retrieval_recall"] == 0.5
    assert metrics["gold_citation_recall"] == 0.5
    assert metrics["citation_from_retrieval"] == 1.0
    assert metrics["required_paper_retrieval_recall"] == 0.5
    assert metrics["required_paper_citation_recall"] == 0.5
    assert metrics["all_required_papers_retrieved"] == 0.0


def test_required_numeric_values_cap_correctness_when_a_range_endpoint_is_missing():
    question = {"id": "q0054", "kind": "cross_paper",
                "required_numeric_values": ["1130", "1627", "1514", "137", "26", "30", "45"]}
    answer = "Range 1154–1627; N IV 1514 ± 137; minimum 26 vs typical 30–45."
    metrics = runner.deterministic_metrics(question, [], [], answer)
    judge_result = {"correctness": 1.0, "groundedness": 1.0,
                    "answer_relevance": 1.0, "abstention": "not_applicable"}
    adjusted, safeguards = runner.apply_judge_safeguards(
        question, metrics, [], judge_result, answer,
    )

    assert metrics["required_numeric_value_recall"] == 6 / 7
    assert metrics["missing_required_numeric_values"] == ["1130"]
    assert adjusted["correctness"] == 0.5
    assert safeguards[0]["reason"] == "missing_required_numeric_values"


def test_summary_includes_agentic_termination_and_cost_metadata():
    execution = {
        "stop_reason": "insufficient_evidence",
        "synthesis_policy": "evidence_fallback",
        "rounds": 2,
        "tool_calls": 3,
        "evidence_count": 7,
        "required_evidence_need_count": 3,
        "covered_evidence_need_count": 2,
        "planner_tokens": 900,
        "actions": [
            {"tool": "search_chunks", "status": "success"},
            {"tool": "get_neighbors", "status": "error"},
        ],
    }
    rows = [{"mode": "agentic", "profile": "cross_multihop", "kind": "cross_paper",
             "metrics": {}, "elapsed_seconds": 1.0, "error": None,
             "agent_execution": execution}]

    summary = runner.summarize(rows, ["agentic"])["agentic"]["agent_execution"]

    assert summary["stop_reasons"] == {"insufficient_evidence": 1}
    assert summary["synthesis_policies"] == {"evidence_fallback": 1}
    assert summary["mean_rounds"] == 2.0
    assert summary["tool_usage"] == {"get_neighbors": 1, "search_chunks": 1}
    assert summary["tool_errors"] == 1
    assert summary["mean_atomic_evidence_needs"] == 3.0
    assert summary["atomic_need_full_coverage_rate"] == 0.0


def test_agentic_summary_reports_preflight_token_requirement():
    row = {"mode": "agentic", "profile": "cross_multihop", "kind": "cross_paper",
           "metrics": {}, "elapsed_seconds": 1.0, "error": None,
           "agent_execution": {
               "stop_reason": "token_budget", "planner_tokens": 10000,
               "next_call_estimated_tokens": 12000, "actions": [],
           }}
    execution = runner.summarize([row], ["agentic"])["agentic"]["agent_execution"]
    assert execution["preflight_stop_runs"] == 1
    assert execution["mean_preflight_required_total_tokens"] == 22000.0


def test_agentic_summary_records_planner_context_compaction():
    rows = [{"mode": "agentic", "profile": "single_fact", "kind": "single_paper",
             "metrics": {}, "elapsed_seconds": 1.0, "error": None,
             "agent_execution": {"stop_reason": "sufficient", "actions": [],
                                 "planner_context_compactions": count}}
            for count in (0, 1, 2)]
    summary = runner.summarize(rows, ["agentic"])["agentic"]["agent_execution"]
    assert summary["planner_context_compaction_runs"] == 2


def test_agentic_summary_distinguishes_blocked_compaction_attempt_from_used_context():
    row = {"mode": "agentic", "profile": "single_fact", "kind": "single_paper",
        "metrics": {}, "elapsed_seconds": 1.0, "error": None, "agent_execution": {
            "stop_reason": "token_budget", "actions": [], "planner_context_compactions": 0,
            "planner_context_compaction_attempts": 1}}
    summary = runner.summarize([row], ["agentic"])["agentic"]["agent_execution"]
    assert summary["planner_context_compaction_attempt_runs"] == 1
    assert summary["planner_context_compaction_runs"] == 0


def test_agentic_summary_records_bounded_requirement_correction():
    rows = [{"mode": "agentic", "profile": "single_fact", "kind": "single_paper",
             "metrics": {}, "elapsed_seconds": 1.0, "error": None,
             "agent_execution": execution} for execution in (
                 {"stop_reason": "sufficient", "actions": []},  # Historical metadata.
                 {"stop_reason": "token_budget", "actions": [],
                  "requirement_correction_attempts": 0,
                  "requirement_validation_failures": [{"attempt": 1, "issues": []}]},
                 {"stop_reason": "sufficient", "actions": [],
                  "requirement_correction_attempts": 1,
                  "requirement_validation_failures": [{"attempt": 1, "issues": []}]},
             )]
    summary = runner.summarize(rows, ["agentic"])["agentic"]["agent_execution"]
    assert summary["requirement_correction_runs"] == 1
    assert summary["requirement_validation_failure_runs"] == 2


def test_summary_counts_safe_generation_abstentions():
    rows = [{
        "mode": "hybrid", "profile": "cross_multihop", "kind": "cross_paper",
        "metrics": {}, "elapsed_seconds": 1.0, "error": None,
        "generation_diagnostics": {
            "status": "safe_abstention", "reason": "citation_validation_failed",
        },
    }]

    summary = runner.summarize(rows, ["hybrid"])["hybrid"]

    assert summary["errors"] == 0
    assert summary["generation_diagnostics"] == {
        "runs": 1,
        "statuses": {"safe_abstention": 1},
        "reasons": {"citation_validation_failed": 1},
    }


def test_judge_consistency_summary_and_report_keep_flagged_scores_and_skip_historical_runs():
    rows = [{"question_id": f"q{index}", "mode": "hybrid", "kind": "single_paper",
             "metrics": {"answer_correctness": 0.5}, "elapsed_seconds": 1.0, "error": None,
             "judge_request": metadata} for index, metadata in enumerate([
        {"reference": {"consistency_status": "needs_review", "consistency_validation_failures": [{}]}},
        {"reference": {"consistency_status": "no_detected_conflict", "consistency_validation_failures": [{}]}},
        {"reference": {"attempts": 1}},  # Legacy result without checks is not assumed clean.
        None,
    ])]
    summary = runner.summarize(rows, ["hybrid"])["hybrid"]
    assert summary["judge_consistency"] == {
        "runs": 2, "statuses": {"needs_review": 1, "no_detected_conflict": 1},
        "flagged_runs": 2, "needs_review_question_ids": ["q0"],
    }
    assert summary["questions"] == 4
    assert summary["errors"] == 0
    assert summary["metrics"]["answer_correctness"] == 0.5
    assert summary["profiles"]["single_paper"]["judge_consistency"] == summary["judge_consistency"]
    report = runner.report_markdown(
        {"run_id": "run", "dataset_hash": "hash", "modes": ["hybrid"]}, {"hybrid": summary})
    assert "Judge consistency" in report
    assert "question IDs still needing review: q0" in report
    assert "null/unscored, not zero or a promoted score" in report
    assert runner._summarize_judge_consistency(rows[2:]) is None


@pytest.mark.parametrize("status", ["needs_review", "no_detected_conflict"])
def test_quote_failures_count_as_flagged_even_without_semantic_conflicts(status):
    summary = runner._summarize_judge_consistency([{
        "question_id": "q1", "judge_request": {"reference": {
            "consistency_status": status, "quote_validation_failures": [{"attempt": 1}],
            "consistency_validation_failures": [],
        }},
    }])
    assert summary["flagged_runs"] == 1
    assert summary["needs_review_question_ids"] == (["q1"] if status == "needs_review" else [])


def test_claim_anchors_only_use_exact_rendered_answer_and_cover_gaps_without_truncation():
    text = "A long method explanation. " * 40 + "cluster structure"
    answer = text + "\n\nA requested measurement is unavailable."
    claims = [{"text": text}, {"text": text}, {"text": "Unrendered phantom fact."}]
    anchors = runner._answer_anchors(answer, claims)
    assert [row["text"] for row in anchors] == [text, "A requested measurement is unavailable."]
    assert [row["id"] for row in anchors] == ["a0001", "a0002"]
    assert anchors[0]["source"] == "claim"
    assert anchors[1]["source"] == "answer_span"
    assert runner._answer_anchors(answer, claims) == anchors
    resolved = runner._resolve_answer_claims({"answer_checks": {"q_original": [{
        "answer_claim_ids": ["a0001", "a0002"],
    }]}}, anchors)
    assert resolved["answer_checks"]["q_original"][0]["answer_quotes"] == [row["text"] for row in anchors]
    assert runner._invalid_answer_quotes(resolved["answer_checks"], answer) == []
    assert runner._answer_anchors("", [{"text": "not rendered"}]) == []


def test_claim_ids_are_schema_enums_not_free_text_or_quotes():
    from pydantic import ValidationError

    anchors = runner._answer_anchors("The mass is 8 solar masses.", None)
    schema = runner._reference_judge_schema([("q_original", "Report mass.")], anchors)
    check = answer_check()
    check.pop("answer_quotes")
    check["answer_claim_ids"] = ["a0001"]
    payload = {"correctness": 1, "answer_relevance": 1, "abstention": "not_applicable",
               "reason": "Fixture.", "answer_checks": {"q_original": [check]}}
    schema.model_validate(payload)
    check["answer_claim_ids"] = ["not-an-answer-id"]
    with pytest.raises(ValidationError):
        schema.model_validate(payload)
    check["answer_claim_ids"] = ["a0001"]
    check["answer_quotes"] = ["A rewritten quote."]
    with pytest.raises(ValidationError):
        schema.model_validate(payload)
    check.pop("answer_quotes")
    check["answer_claim_ids"] = []
    schema = runner._reference_judge_schema([("q_original", "Report mass.")], [])
    schema.model_validate(payload)
    check["answer_claim_ids"] = ["a0001"]
    with pytest.raises(ValidationError):
        schema.model_validate(payload)


def test_selected_claim_with_missing_numeric_target_still_caps_correctness():
    answer = "The mass is 8 solar masses."
    check = answer_check(values=("9",))
    check.pop("answer_quotes")
    check["answer_claim_ids"] = ["a0001"]
    assessment = runner._resolve_answer_claims(
        {"correctness": 1, "answer_checks": [check]}, runner._answer_anchors(answer, None))
    adjusted, safeguards = runner.apply_judge_safeguards(
        {"kind": "single_paper"}, {}, ["point"], assessment, answer)
    assert adjusted["correctness"] == 0.5
    assert safeguards[0]["checks"][0]["missing_numeric_values"] == ["9"]


@pytest.mark.parametrize("scored_value", [None, 0.0, 1.0])
def test_summary_reports_correctness_denominator_without_treating_null_as_zero(scored_value):
    values = [None, scored_value]
    rows = [{"question_id": f"q{index}", "mode": "agentic", "kind": "single_paper",
             "profile": "single_fact", "elapsed_seconds": 1, "error": None,
             "metrics": {"answer_correctness": value, "groundedness": 1, "retrieval_recall": 1}}
            for index, value in enumerate(values)]
    summary = runner.summarize(rows, ["agentic"])["agentic"]
    assert summary["metrics"]["answer_correctness"] == scored_value
    scored = int(scored_value is not None)
    assert summary["metric_sample_counts"]["answer_correctness"] == {"scored": scored, "unscored": 2 - scored}
    assert summary["metric_sample_counts"]["groundedness"] == {"scored": 2, "unscored": 0}
    assert summary["profiles"]["single_fact"]["metric_sample_counts"] == summary["metric_sample_counts"]
    report = runner.report_markdown(
        {"run_id": "offline", "dataset_hash": "hash", "modes": ["agentic"]}, {"agentic": summary})
    assert "Correctness scored / unscored" in report
    assert f"| {scored} / {2 - scored} |" in report
    assert "NaN" not in json.dumps(summary)


def test_stage_timings_aggregate_only_measured_stages():
    rows = [
        {"mode": "hybrid_rerank", "profile": "single_fact", "kind": "single_paper",
         "metrics": {}, "elapsed_seconds": 8.0, "error": None,
         "stage_timings": {"pipeline_seconds": 5.0, "retrieval_seconds": 2.0,
                           "rerank_seconds": 1.0, "judge_reference_seconds": 1.5,
                           "judge_grounding_seconds": 1.0}},
        {"mode": "hybrid_rerank", "profile": "single_fact", "kind": "single_paper",
         "metrics": {}, "elapsed_seconds": 10.0, "error": None,
         "stage_timings": {"pipeline_seconds": 7.0, "retrieval_seconds": 4.0,
                           "judge_reference_seconds": 1.5,
                           "judge_grounding_seconds": 1.0}},
    ]
    summary = runner.summarize(rows, ["hybrid_rerank"])["hybrid_rerank"]
    assert summary["stage_timings"]["mean_seconds"]["pipeline_seconds"] == 6.0
    assert summary["stage_timings"]["mean_seconds"]["retrieval_seconds"] == 3.0
    assert summary["stage_timings"]["mean_seconds"]["rerank_seconds"] == 1.0
    assert summary["stage_timings"]["sample_counts"]["rerank_seconds"] == 1
    report = runner.report_markdown(
        {"run_id": "run", "dataset_hash": "hash", "modes": ["hybrid_rerank"]},
        {"hybrid_rerank": summary},
    )
    assert "Mean stage timings" in report
    assert "| hybrid_rerank | 6.000 | 3.000 | 1.000 |" in report


def test_rerank_diagnostics_distinguish_candidate_and_selection_coverage():
    diagnostics = runner._retrieval_diagnostics_payload(
        {"paper_ids": ["paper-a", "paper-b"]},
        {"candidate_count": 20, "selected_count": 5,
         "candidate_paper_count": 3, "selected_paper_count": 1,
         "candidate_paper_ids": ["paper-a", "paper-b", "distractor"],
         "selected_paper_ids": ["paper-a"], "ranked_candidates": []},
    )
    row = {"mode": "hybrid_rerank", "profile": "cross_comparison",
           "kind": "cross_paper", "metrics": {}, "elapsed_seconds": 1.0,
           "error": None, "retrieval_diagnostics": diagnostics}

    summary = runner.summarize([row], ["hybrid_rerank"])["hybrid_rerank"][
        "retrieval_diagnostics"
    ]

    assert diagnostics["required_paper_candidate_recall"] == 1.0
    assert diagnostics["required_paper_selected_recall"] == 0.5
    assert summary["all_required_papers_candidate_rate"] == 1.0
    assert summary["all_required_papers_selected_rate"] == 0.0


def test_agentic_synthesis_timings_aggregate_and_render_optional_repair():
    rows = [
        {"mode": "agentic", "kind": "single_paper", "metrics": {},
         "elapsed_seconds": 6, "error": None, "stage_timings": {
             "generation_seconds": 5, "agentic_draft_seconds": 2,
             "agentic_verify_seconds": 3}},
        {"mode": "agentic", "kind": "single_paper", "metrics": {},
         "elapsed_seconds": 12, "error": None, "stage_timings": {
             "generation_seconds": 11, "agentic_draft_seconds": 4,
             "agentic_verify_seconds": 6, "agentic_repair_seconds": 1}},
    ]
    summary = runner.summarize(rows, ["agentic"])
    means = summary["agentic"]["stage_timings"]["mean_seconds"]
    assert means["agentic_draft_seconds"] == 3
    assert means["agentic_verify_seconds"] == 4.5
    assert means["agentic_repair_seconds"] == 1
    assert summary["agentic"]["stage_timings"]["sample_counts"]["agentic_repair_seconds"] == 1
    manifest = {"run_id": "run", "dataset_hash": "hash", "modes": ["agentic"]}
    report = runner.report_markdown(manifest, summary)
    assert "Agentic synthesis breakdown" in report
    assert "| agentic | 3.000 | 4.500 | 1.000 |" in report
    no_repair = runner.report_markdown(manifest, runner.summarize(rows[:1], ["agentic"]))
    assert "| agentic | 2.000 | 3.000 | — |" in no_repair


def test_evaluate_item_persists_pipeline_and_judge_stage_timings(monkeypatch):
    import src.api.rag.retrieval as retrieval

    def fake_pipeline(*args, stage_timings, **kwargs):
        stage_timings.update(retrieval_seconds=0.2, generation_seconds=0.3)
        return {"answer": "A result.", "retrieved_chunks": [], "cited_context_ids": [],
                "claims": [], "execution": None}

    def fake_judge(*args, stage_timings, **kwargs):
        stage_timings.update(judge_reference_seconds=0.1,
                             judge_grounding_seconds=0.1)
        return ({"correctness": 1.0, "groundedness": 1.0,
                 "answer_relevance": 1.0, "abstention": "not_applicable",
                 "reason": "Offline fixture."}, {})

    monkeypatch.setattr(retrieval, "rag_pipeline", fake_pipeline)
    monkeypatch.setattr(runner, "judge", fake_judge)
    monkeypatch.setattr(runner, "trace_attributes", lambda **kwargs: nullcontext())
    monkeypatch.setattr(runner, "observation", lambda **kwargs: nullcontext(None))
    monkeypatch.setattr(runner, "score_trace", Mock())

    record = runner.evaluate_item(
        {"id": "q1", "kind": "single_paper", "profile": "single_fact",
         "question": "What happened?", "reference_answer": "A result.",
         "reference_evidence": []},
        "hybrid", qdrant=Mock(), collection="papers", scope=Mock(), top_k=5,
        generation_model="offline", judge_enabled=True, judge_model="offline",
        judge_reasoning_effort="minimal", run_id="offline", catalogue=Mock(),
    )
    assert record["error"] is None
    timings = record["stage_timings"]
    assert timings["retrieval_seconds"] == 0.2
    assert timings["generation_seconds"] == 0.3
    assert timings["judge_reference_seconds"] == 0.1
    assert timings["judge_grounding_seconds"] == 0.1
    assert timings["pipeline_seconds"] >= 0
    assert timings["judge_seconds"] >= 0


def test_unexpected_judge_connection_failure_preserves_completed_pipeline(monkeypatch):
    import src.api.rag.retrieval as retrieval
    import httpx

    chunks = [{"id": "p1", "paper_id": "paper-1", "text": "A result."}]
    claims = [{"text": "A result.", "cited_context_ids": ["p1"], "need_ids": []}]
    execution = {"stop_reason": "sufficient", "rounds": 1, "actions": []}
    generation = {"status": "complete", "reason": "verified_answer"}
    monkeypatch.setattr(retrieval, "rag_pipeline", lambda *a, **kw: {
        "answer": "A result.", "retrieved_chunks": chunks, "claims": claims,
        "cited_context_ids": ["p1"], "execution": execution, "generation_diagnostics": generation})

    def failing_judge(*args, stage_timings, **kwargs):
        stage_timings["judge_reference_seconds"] = 0.1
        raise httpx.RemoteProtocolError("private endpoint or credential must not be logged")

    monkeypatch.setattr(runner, "judge", failing_judge)
    monkeypatch.setattr(runner, "trace_attributes", lambda **kwargs: nullcontext())
    span = Mock()
    monkeypatch.setattr(runner, "observation", lambda **kwargs: nullcontext(span))
    monkeypatch.setattr(runner, "score_trace", Mock())
    record = runner.evaluate_item(
        {"id": "q1", "kind": "single_paper", "question": "What happened?",
         "reference_answer": "A result.", "reference_evidence": [{"point_id": "p1"}],
         "paper_ids": ["paper-1"]}, "agentic", qdrant=Mock(), collection="papers", scope=Mock(),
        top_k=5, generation_model="offline", judge_enabled=True, judge_model="offline",
        judge_reasoning_effort="minimal", run_id="offline")
    assert record["error"] is None
    assert record["judge_error"]["judge"]["category"] == "connection_interrupted"
    assert record["answer"] == "A result."
    assert record["claims"] == claims
    assert record["retrieved_chunks"] == chunks
    assert record["agent_execution"] == execution
    assert record["generation_diagnostics"] == generation
    assert record["metrics"]["retrieval_recall"] == 1
    assert record["metrics"]["answer_correctness"] is None
    assert record["metrics"]["groundedness"] is None
    assert "private endpoint" not in json.dumps(record)
    assert {call.args[0] for call in runner.score_trace.call_args_list}.isdisjoint(
        {"answer_correctness", "groundedness", "answer_relevance"})
    summary = runner.summarize([record], ["agentic"])["agentic"]
    assert summary["errors"] == 0
    assert summary["judge_errors"] == 1
    assert summary["metric_sample_counts"]["groundedness"] == {"scored": 0, "unscored": 1}
    assert span.update.call_args.kwargs["status_message"] == "judge_failed_answer_preserved"


def test_unscored_grounding_cannot_be_manufactured_by_paper_coverage_safeguards():
    result, safeguards = runner.apply_judge_safeguards(
        {"kind": "cross_paper"}, {"all_required_papers_retrieved": 0}, ["p1"],
        {"correctness": None, "groundedness": None}, "A result.", [{"text": "A result."}])
    assert result["groundedness"] is None
    assert safeguards == []


def test_judge_retries_one_invalid_structured_response(monkeypatch):
    monkeypatch.setattr(runner.config, "EVAL_JUDGE_MAX_OUTPUT_TOKENS", 32768)
    invalid = SimpleNamespace(id="response-1", model="judge", output_text="{}",
                              output=[], status="incomplete", output_parsed=None,
                              usage=SimpleNamespace(model_dump=lambda: {"input_tokens": 10}))
    valid = SimpleNamespace(id="response-2", model="judge", _request_id="request-2",
                            status="completed", output=[],
                            output_text=json.dumps({"correctness": 1,
                                "answer_relevance": 1, "abstention": "not_applicable",
                                "reason": "Matches the reference.",
                                "answer_checks": {"q_original": [{
                                    "requested_fact": "Report the result.", "status": "answered",
                                    "answer_claim_ids": ["a0001"], "required_numeric_values": [],
                                    "missing_or_incorrect_detail": "",
                                    "deficit_basis": "none", "claimed_missing_answer_fragments": [],
                                }]}}),
                            usage=SimpleNamespace(model_dump=lambda: {"input_tokens": 11}))
    grounded = SimpleNamespace(id="response-3", model="judge", _request_id="request-3",
                               status="completed", output=[],
                               output_text=json.dumps({"groundedness": 0.5,
                                   "reason": "One claim lacks retrieved support."}),
                               usage=SimpleNamespace(model_dump=lambda: {"input_tokens": 7}))
    valid.output_parsed = runner._reference_judge_schema(
        [("q_original", "Question?")], runner._answer_anchors("Answer.", None)).model_validate_json(
        valid.output_text)
    grounded.output_parsed = runner.GroundingJudgeResult.model_validate_json(grounded.output_text)
    create = Mock(side_effect=[invalid, valid, grounded])
    client = Mock()
    client.with_options.return_value = client
    client.responses.parse = create
    monkeypatch.setattr("src.api.core.clients.openai_client", Mock(return_value=client))

    timings = {}
    result, metadata = runner.judge(
        {"kind": "single_paper", "question": "Question?", "reference_answer": "Answer.",
         "reference_evidence": []}, "Answer.", [], "gpt-5-mini", "minimal",
        stage_timings=timings)
    assert timings["judge_reference_seconds"] >= 0
    assert timings["judge_grounding_seconds"] >= 0

    assert result["correctness"] == 1
    assert result["groundedness"] == 0.5
    assert create.call_count == 3
    assert [row.kwargs["max_output_tokens"] for row in create.call_args_list] == [32768] * 3
    assert "text" not in create.call_args.kwargs
    assert create.call_args.kwargs["text_format"].__name__ == "ScopedGroundingJudgeResult"
    client.with_options.assert_has_calls([call(max_retries=0)] * 2)
    assert metadata["reference"]["attempts"] == 2
    assert metadata["reference"]["response_ids"] == ["response-1", "response-2"]
    assert metadata["reference"]["usage"]["input_tokens"] == 21
    assert metadata["grounding"]["response_ids"] == ["response-3"]
    assert metadata["reference"]["max_output_tokens"] == 32768
    assert metadata["grounding"]["max_output_tokens"] == 32768
    grounding_payload = json.loads(create.call_args_list[-1].kwargs["input"])
    assert "reference_answer" not in grounding_payload
    assert "reference_evidence" not in grounding_payload


def answer_check(*, status="answered", quotes=("The mass is 8 solar masses.",), values=("8",),
                 detail=None, basis=None, fragments=()):
    if detail is None:
        detail = "" if status == "answered" else "The requested measurement uncertainty is absent."
    return {"requested_fact": "Report the mass.", "status": status,
            "answer_quotes": list(quotes), "required_numeric_values": list(values),
            "missing_or_incorrect_detail": detail,
            "deficit_basis": basis or ("none" if status == "answered" else "missing_content"),
            "claimed_missing_answer_fragments": list(fragments)}


@pytest.mark.parametrize("status", ["partial", "missing", "incorrect"])
@pytest.mark.parametrize("detail", ["", "   "])
def test_non_full_judge_verdict_requires_an_explicit_deficit(status, detail):
    parsed = runner.ReferenceAnswerCheck.model_validate(answer_check(status=status, detail=detail))
    failure = runner._inconsistent_reference_checks([parsed.model_dump()], "The mass is 8 solar masses.")
    assert "non_full_without_deficit" in failure[0]["reasons"]


def test_judge_detail_is_required_even_for_answered_checks():
    from pydantic import ValidationError
    check = answer_check()
    check.pop("missing_or_incorrect_detail")
    with pytest.raises(ValidationError) as caught:
        runner.ReferenceAnswerCheck.model_validate(check)
    assert caught.value.errors()[0]["loc"] == ("missing_or_incorrect_detail",)


def test_answered_verdict_cannot_also_claim_an_unresolved_deficit():
    parsed = runner.ReferenceAnswerCheck.model_validate(answer_check(detail="The unit is missing."))
    failure = runner._inconsistent_reference_checks([parsed.model_dump()], "The mass is 8 solar masses.")
    assert "answered_with_deficit" in failure[0]["reasons"]


def test_explained_partial_verdict_is_not_promoted_when_numeric_targets_match():
    check = runner.ReferenceAnswerCheck.model_validate(answer_check(
        status="partial", detail="The requested uncertainty is absent, although the mass is given."))
    result, safeguards = runner.apply_judge_safeguards(
        {"kind": "single_paper"}, {}, ["point"],
        {"correctness": 1, "answer_checks": [check.model_dump()]}, "The mass is 8 solar masses.")
    assert result["correctness"] == 0.5
    assert safeguards[0]["checks"][0]["missing_numeric_values"] == []
    assert result["answer_checks"][0]["missing_or_incorrect_detail"] == check.missing_or_incorrect_detail


@pytest.mark.parametrize("check", [
    answer_check(basis="missing_content"),
    answer_check(status="partial", basis="none"),
    answer_check(status="incorrect", basis="incorrect_content", fragments=("8",)),
    answer_check(status="partial", fragments=("   ",)),
])
def test_judge_deficit_basis_and_fragment_pairing_is_reviewable_not_a_parse_error(check):
    parsed = runner.ReferenceAnswerCheck.model_validate(check)
    assert runner._inconsistent_reference_checks([parsed.model_dump()], "The mass is 8 solar masses.")


@pytest.mark.parametrize("field", ["deficit_basis", "claimed_missing_answer_fragments"])
def test_judge_consistency_fields_are_required(field):
    from pydantic import ValidationError
    check = answer_check()
    check.pop(field)
    with pytest.raises(ValidationError) as caught:
        runner.ReferenceAnswerCheck.model_validate(check)
    assert caught.value.errors()[0]["loc"] == (field,)


def test_alleged_literal_omission_is_checked_against_whole_answer_not_only_selected_quote():
    answer = "We partition the primaries. Central stars are within 20% of the half-mass radius."
    check = answer_check(status="partial", quotes=("We partition the primaries.",), values=(),
                         fragments=("20% of the half-mass radius",))
    failures = runner._inconsistent_reference_checks({"q_2": [check]}, answer)
    assert failures == [{"check_index": 0, "reasons": ["claimed_missing_fragment_present"],
                         "present_fragment_count": 1}]
    # The safeguard still does not auto-promote this contradictory verdict.
    adjusted, _ = runner.apply_judge_safeguards(
        {"kind": "single_paper"}, {}, ["point"],
        {"correctness": 1, "answer_checks": [check]}, answer)
    assert adjusted["correctness"] == 0.5


@pytest.mark.parametrize("answer,fragment", [
    ("The mass is 80 solar masses.", "8 solar masses"),
    ("The mass is 8 solar masses.", "uncertainty"),
    ("The threshold is 20%.", "20% of the half-mass radius"),
])
def test_true_omissions_are_not_inconsistent_or_reinterpreted_as_full_coverage(answer, fragment):
    check = answer_check(status="partial", fragments=(fragment,))
    assert runner._inconsistent_reference_checks([check], answer) == []


def test_existing_but_wrong_statement_is_not_confused_with_literal_omission():
    check = answer_check(status="incorrect", basis="incorrect_content",
                         detail="Expected 9 solar masses, but the answer reports 8.")
    assert runner._inconsistent_reference_checks([check], "The mass is 8 solar masses.") == []


@pytest.mark.parametrize("question,metrics,answer,claims", [
    ({"kind": "single_paper"}, {}, "The mass is 8 solar masses.", None),
    ({"kind": "single_paper"}, {"missing_required_numeric_values": ["8"]}, "Some mass.", None),
    ({"kind": "cross_paper", "question": "Compare these papers."}, {}, "Some mass.", None),
    ({"kind": "single_paper"}, {}, "I cannot answer this question from the available evidence.", []),
])
def test_score_safeguards_never_manufacture_a_score_for_unresolved_judge_review(question, metrics, answer, claims):
    adjusted, adjustments = runner.apply_judge_safeguards(
        question, metrics, ["point"], {"correctness": None, "groundedness": 1,
            "reference_score_status": "unscored_needs_review", "answer_checks": [answer_check(status="partial")]},
        answer, claims)
    assert adjusted["correctness"] is None
    assert adjusted["groundedness"] == 1
    assert adjustments == []


def test_reference_ambiguity_is_a_review_flag_not_a_proven_answer_error():
    check = answer_check(status="partial", basis="reference_ambiguity", values=(),
                         detail="Main text and figure labels give conflicting exponents.")
    assert runner._inconsistent_reference_checks([check], "The mass is 8 solar masses.") == [
        {"check_index": 0, "reasons": ["unresolved_reference_ambiguity"], "present_fragment_count": 0}]


def test_reference_judge_instructions_distinguish_clear_sources_from_damaged_picture_labels():
    instructions = runner.REFERENCE_JUDGE_INSTRUCTIONS
    assert "SAME quantity, entity and simulation case" in instructions
    assert "Never guess a missing sign" in instructions
    assert "Do not demand that the answer" in instructions
    assert "Do not substitute a different parameter or case" in instructions
    assert "reference_ambiguity" in instructions


@pytest.mark.parametrize("value", ["[]", "[Rout = Rsg]", "1e-3", "8 solar masses", "NaN", "Infinity", 8])
def test_judge_numeric_targets_reject_non_decimal_or_symbolic_values(value):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        runner.ReferenceAnswerCheck.model_validate(answer_check(values=(value,)))


@pytest.mark.parametrize("values", [(), ("0", "-2", "0.0008", "0.0006", "8.25")])
def test_judge_numeric_targets_accept_real_empty_arrays_and_decimal_strings(values):
    parsed = runner.ReferenceAnswerCheck.model_validate(answer_check(values=values))
    assert parsed.required_numeric_values == list(values)


@pytest.mark.parametrize("check", [
    answer_check(quotes=("The mass is 9 solar masses.",), values=("9",)),
    answer_check(quotes=()),
    answer_check(values=("9",)),
    answer_check(status="partial"),
    answer_check(status="missing"),
    answer_check(status="incorrect"),
])
def test_correctness_cannot_use_reference_facts_as_answer_support(check):
    result, safeguards = runner.apply_judge_safeguards(
        {"kind": "single_paper"}, {}, ["point"],
        {"correctness": 1.0, "answer_checks": [check]}, "The mass is 8 solar masses.")
    assert result["correctness"] == 0.5
    assert safeguards[0]["reason"] == "reference_assessment_not_answer_anchored"


def test_answer_anchoring_preserves_valid_scores_and_normalizes_whitespace():
    result, safeguards = runner.apply_judge_safeguards(
        {"kind": "single_paper"}, {}, ["point"],
        {"correctness": 1.0, "answer_checks": [answer_check()]},
        "The mass\nis 8 solar masses.")
    assert result["correctness"] == 1
    assert safeguards == []


def test_answer_anchoring_accepts_capitalization_but_not_changed_values():
    answer = "For this model, the rate is 8 × 10^-4 M⊙ yr^-1."
    for quote, expected in [(answer.lower(), 1), (answer.replace("8 ×", "6 ×"), 0.5)]:
        result, safeguards = runner.apply_judge_safeguards(
            {"kind": "single_paper"}, {}, ["point"],
            {"correctness": 1, "answer_checks": [answer_check(
                quotes=(quote,), values=("0.0008",))]}, answer)
        assert result["correctness"] == expected
        assert bool(safeguards) == (expected != 1)


@pytest.mark.parametrize("answer,values", [
    ("The rate is (2–5) × 10^-4 M⊙ yr^-1.", ("0.0002", "0.0005")),
    ("The model includes 50% primordial binaries.", ("0.5",)),
])
def test_answer_anchoring_normalizes_scientific_ranges_and_explicit_percentages(answer, values):
    result, safeguards = runner.apply_judge_safeguards(
        {"kind": "single_paper"}, {}, ["point"],
        {"correctness": 1, "answer_checks": [answer_check(quotes=(answer,), values=values)]}, answer)
    assert result["correctness"] == 1
    assert safeguards == []


def test_bare_counts_do_not_become_fractions_and_short_numeric_quotes_do_not_match_longer_values():
    answer = "The model includes 50 systems. The mass is 80 solar masses."
    assert not runner._valid_answer_quote(answer, "The mass is 8")
    result, safeguards = runner.apply_judge_safeguards(
        {"kind": "single_paper"}, {}, ["point"],
        {"correctness": 1, "answer_checks": [answer_check(
            quotes=("The model includes 50 systems.",), values=("0.5",))]}, answer)
    assert result["correctness"] == 0.5
    assert safeguards[0]["checks"][0]["missing_numeric_values"] == ["0.5"]


@pytest.mark.parametrize("quote", [
    "The model measures companions ... to constrain supply.",
    "The model measures companions to constrain supply.",
])
def test_answer_anchoring_does_not_license_stitched_or_paraphrased_quotes(quote):
    answer = "The model measures companions. We propose using these counts to constrain supply."
    result, safeguards = runner.apply_judge_safeguards(
        {"kind": "single_paper"}, {}, ["point"],
        {"correctness": 1, "answer_checks": [answer_check(quotes=(quote,), values=())]}, answer)
    assert result["correctness"] == 0.5
    assert safeguards[0]["checks"][0]["invalid_quote_count"] == 1


@pytest.mark.parametrize("second_quote,expected", [
    ("The mass is 8 solar masses.", 1),
    ("The mass ... is 8 solar masses.", None),
])
def test_judge_quote_repair_shares_the_existing_retry_bound(monkeypatch, second_quote, expected):
    answer = "The mass is 8 solar masses."
    schema = runner._reference_judge_schema([("q_original", "Report the mass.")])

    def response(identifier, quote):
        parsed = schema.model_validate({
            "correctness": 1, "answer_relevance": 1, "abstention": "not_applicable",
            "reason": "Mock assessment.", "answer_checks": {"q_original": [answer_check(quotes=(quote,))]},
        })
        return SimpleNamespace(id=identifier, model="judge", status="completed", output=[],
                               output_parsed=parsed, usage=SimpleNamespace(
                                   model_dump=lambda: {"input_tokens": 10, "output_tokens": 5}))

    client = Mock()
    client.with_options.return_value = client
    client.responses.parse.side_effect = [
        response("first", "The mass ... is 8 solar masses."), response("second", second_quote)]
    monkeypatch.setattr("src.api.core.clients.openai_client", Mock(return_value=client))
    result, metadata = runner._judge_request(
        instructions=runner.REFERENCE_JUDGE_INSTRUCTIONS, payload={"actual_answer": answer},
        schema=schema, model="offline", reasoning_effort="minimal", answer_for_quotes=answer)
    assert client.responses.parse.call_count == 2
    assert metadata["attempts"] == 2
    assert metadata["usage"]["input_tokens"] == 20
    assert metadata["usage"]["output_tokens"] == 10
    assert metadata["response_ids"] == ["first", "second"]
    assert metadata["quote_validation_failures"][0]["attempt"] == 1
    second_input = json.loads(client.responses.parse.call_args.kwargs["input"])
    assert second_input["actual_answer"] == answer
    assert "quote_format_feedback" in second_input
    result["answer_checks"] = result["answer_checks"]["q_original"]
    adjusted, _ = runner.apply_judge_safeguards({"kind": "single_paper"}, {}, ["point"], result, answer)
    assert adjusted["correctness"] == expected


@pytest.mark.parametrize("schema_failure_first", [False, True])
def test_genuine_missing_fact_is_not_retried_and_schema_quote_failures_share_one_retry(
        monkeypatch, schema_failure_first):
    schema = runner._reference_judge_schema([("q_original", "Report the mass.")])
    parsed = schema.model_validate({
        "correctness": 0.5, "answer_relevance": 0.5, "abstention": "not_applicable",
        "reason": "Mock assessment.", "answer_checks": {"q_original": [answer_check(
            status="answered" if schema_failure_first else "missing",
            quotes=("Invented answer ... text.",) if schema_failure_first else (), values=("8",))]},
    })
    valid = SimpleNamespace(id="valid", model="judge", status="completed", output=[],
                            output_parsed=parsed, usage=None)
    invalid = SimpleNamespace(id="invalid", model="judge", status="incomplete", output=[],
                              output_parsed=None, usage=None)
    client = Mock()
    client.with_options.return_value = client
    client.responses.parse.side_effect = [invalid, valid] if schema_failure_first else [valid]
    monkeypatch.setattr("src.api.core.clients.openai_client", Mock(return_value=client))
    _, metadata = runner._judge_request(
        instructions=runner.REFERENCE_JUDGE_INSTRUCTIONS, payload={"actual_answer": "Some answer."},
        schema=schema, model="offline", reasoning_effort="minimal", answer_for_quotes="Some answer.")
    assert client.responses.parse.call_count == (2 if schema_failure_first else 1)
    if schema_failure_first:
        assert metadata["quote_validation_failures"][0]["attempt"] == 2
        assert metadata["usage"]["usage_incomplete"] is True
    else:
        assert metadata["quote_validation_failures"] == []


def test_schema_failure_then_consistency_failure_cannot_trigger_a_third_request(monkeypatch):
    schema = runner._reference_judge_schema([("q_original", "Report the mass.")])
    check = answer_check(status="partial", fragments=("8 solar masses",))
    parsed = schema.model_validate({"correctness": 0.5, "answer_relevance": 1,
        "abstention": "not_applicable", "reason": "Unreconciled omission.",
        "answer_checks": {"q_original": [check]}})
    invalid = SimpleNamespace(id="invalid", status="incomplete", output_parsed=None, output=[], usage=None)
    valid = SimpleNamespace(id="valid", model="judge", status="completed", output=[],
                            output_parsed=parsed, usage=None)
    client = Mock()
    client.with_options.return_value = client
    client.responses.parse.side_effect = [invalid, valid]
    monkeypatch.setattr("src.api.core.clients.openai_client", lambda: client)
    _, metadata = runner._judge_request(
        instructions=runner.REFERENCE_JUDGE_INSTRUCTIONS,
        payload={"actual_answer": "The mass is 8 solar masses."}, schema=schema,
        model="offline", reasoning_effort="minimal", answer_for_quotes="The mass is 8 solar masses.")
    assert client.responses.parse.call_count == 2
    assert metadata["consistency_status"] == "needs_review"
    assert metadata["consistency_validation_failures"][0]["attempt"] == 2


def test_numeric_targets_must_appear_in_the_actual_quoted_answer_not_reference_or_question():
    answer = "The paper compares parameter values A and B."
    result, safeguards = runner.apply_judge_safeguards(
        {"kind": "cross_paper", "reference_answer": "The rate changes from 0.0008 to 0.0006."},
        {}, ["point"], {"correctness": 1.0, "answer_checks": [answer_check(
            quotes=(answer,), values=("0.0008", "0.0006"))]}, answer)
    assert result["correctness"] == 0.5
    assert safeguards[0]["checks"][0]["missing_numeric_values"] == ["0.0008", "0.0006"]


def test_reference_judge_schema_requires_every_numbered_question_part():
    from pydantic import ValidationError

    schema = runner._reference_judge_schema([("q_1", "Report mass."), ("q_2", "Report dependency.")])
    coverage = schema.model_json_schema()["$defs"]["RequiredAnswerChecks"]
    assert coverage["required"] == ["q_1", "q_2"]
    assert coverage["additionalProperties"] is False
    payload = {"correctness": 1, "answer_relevance": 1, "abstention": "not_applicable",
               "reason": "Mock assessment.", "answer_checks": {"q_1": [answer_check()]}}
    with pytest.raises(ValidationError):
        schema.model_validate(payload)
    payload["answer_checks"]["q_2"] = [answer_check(status="missing", quotes=(), values=())]
    schema.model_validate(payload)


def test_answer_anchor_does_not_penalize_a_correct_unanswerable_refusal():
    answer = "The indexed evidence does not report this measurement."
    result, safeguards = runner.apply_judge_safeguards(
        {"kind": "unanswerable_candidate"}, {}, [],
        {"correctness": 1.0, "abstention": "correct", "answer_checks": [answer_check(
            status="missing", quotes=(answer,), values=())]}, answer, [])
    assert result["correctness"] == 1
    assert safeguards == []


def test_cross_paper_groundedness_is_capped_when_required_paper_is_missing():
    adjusted, safeguards = runner.apply_judge_safeguards(
        {"kind": "cross_paper"},
        {"all_required_papers_retrieved": 0.0},
        ["cited-point"],
        {"correctness": 1.0, "groundedness": 1.0, "answer_relevance": 1.0,
         "abstention": "not_applicable", "reason": "Judge was too lenient."},
    )

    assert adjusted["groundedness"] == 0.0
    assert safeguards == [{
        "metric": "groundedness", "from": 1.0, "to": 0.0,
        "reason": "incomplete_required_paper_retrieval",
    }]


def test_groundedness_cap_does_not_penalize_citation_free_safe_abstention():
    adjusted, safeguards = runner.apply_judge_safeguards(
        {"kind": "cross_paper"},
        {"all_required_papers_retrieved": 0.0}, [],
        {"groundedness": 1.0},
    )

    assert adjusted["groundedness"] == 1.0
    assert safeguards == []


@pytest.mark.parametrize("judge_enabled,judge_failed", [(False, False), (True, False), (True, True)])
def test_local_run_checkpoints_both_modes(tmp_path, monkeypatch, judge_enabled, judge_failed):
    monkeypatch.setattr(runner.config, "EVAL_JUDGE_MAX_OUTPUT_TOKENS", 32768)
    dataset = reviewed_dataset(tmp_path / "dataset")
    qdrant = Mock()
    monkeypatch.setattr(runner, "QdrantClient", Mock(return_value=qdrant))
    catalogue = Mock()
    monkeypatch.setattr("src.api.papers.catalogue.Catalogue", Mock(return_value=catalogue))

    def fake_evaluate(question, mode, **kwargs):
        return {"question_id": question["id"], "kind": question["kind"],
                "profile": question.get("profile"), "mode": mode,
                "question": question["question"], "reference_answer": question["reference_answer"],
                "answer": mode, "retrieved_chunks": [], "cited_context_ids": [],
                "metrics": {"retrieval_recall": 1.0}, "judge": None, "judge_request": None,
                "judge_error": {"reference": {"category": "connection"}} if judge_failed else None,
                "elapsed_seconds": 0.1, "error": None}

    monkeypatch.setattr(runner, "evaluate_item", fake_evaluate)
    args = SimpleNamespace(dataset=dataset, output_root=tmp_path / "runs", run_id="run-1",
        modes=["vanilla", "hybrid"], limit=None, top_k=5, generation_model="model",
        split="all",
        judge=judge_enabled, judge_model="judge", judge_reasoning_effort="minimal",
        langfuse=False, concurrency=1)
    output = runner.run(args)
    results = json.loads((output / "results.json").read_text())["results"]
    manifest = json.loads((output / "manifest.json").read_text())
    summary = json.loads((output / "summary.json").read_text())
    assert [row["mode"] for row in results] == ["vanilla", "hybrid"]
    assert manifest["status"] == ("completed_with_judge_errors" if judge_failed else "complete")
    assert manifest["judge_max_output_tokens"] == (32768 if judge_enabled else None)
    assert manifest["question_profiles"] == {"single_fact": 1}
    assert summary["vanilla"]["profiles"]["single_fact"]["questions"] == 1
    assert summary["vanilla"]["judge_errors"] == int(judge_failed)
    assert summary["vanilla"]["errors"] == 0
    assert [row["answer"] for row in results] == ["vanilla", "hybrid"]
    assert (output / "report.md").exists()
    qdrant.close.assert_called_once()


@pytest.mark.parametrize("cap", [256, 16384, 32768, 128000])
def test_judge_cap_loads_from_dotenv_without_reading_project_secrets(tmp_path, monkeypatch, cap):
    from src.api.core.config import Config

    monkeypatch.delenv("EVAL_JUDGE_MAX_OUTPUT_TOKENS", raising=False)
    settings_file = tmp_path / "judge.env"
    settings_file.write_text(f"EVAL_JUDGE_MAX_OUTPUT_TOKENS={cap}\n")
    settings = Config(_env_file=settings_file, OPENAI_API_KEY="offline", GROQ_API_KEY="offline",
                      QDRANT_API_KEY="offline", COHERE_API_KEY="offline", QDRANT_URL="http://localhost:6333")
    assert settings.EVAL_JUDGE_MAX_OUTPUT_TOKENS == cap


def test_judge_cap_defaults_to_16384_when_not_configured(monkeypatch):
    from src.api.core.config import Config

    monkeypatch.delenv("EVAL_JUDGE_MAX_OUTPUT_TOKENS", raising=False)
    settings = Config(_env_file=None, OPENAI_API_KEY="offline", GROQ_API_KEY="offline",
                      QDRANT_API_KEY="offline", COHERE_API_KEY="offline", QDRANT_URL="http://localhost:6333")
    assert settings.EVAL_JUDGE_MAX_OUTPUT_TOKENS == 16384


@pytest.mark.parametrize("cap", [0, 255, 128001, "invalid"])
def test_judge_cap_rejects_invalid_or_out_of_bounds_values(cap):
    from pydantic import ValidationError
    from src.api.core.config import Config

    with pytest.raises(ValidationError) as caught:
        Config(_env_file=None, OPENAI_API_KEY="offline", GROQ_API_KEY="offline",
               QDRANT_API_KEY="offline", COHERE_API_KEY="offline", QDRANT_URL="http://localhost:6333",
               EVAL_JUDGE_MAX_OUTPUT_TOKENS=cap)
    assert {tuple(row["loc"]) for row in caught.value.errors()} == {("EVAL_JUDGE_MAX_OUTPUT_TOKENS",)}
