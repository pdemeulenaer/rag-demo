import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

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


def test_judge_retries_one_invalid_structured_response(monkeypatch):
    invalid = SimpleNamespace(id="response-1", model="judge", output_text="{}",
                              usage=SimpleNamespace(model_dump=lambda: {"input_tokens": 10}))
    valid = SimpleNamespace(id="response-2", model="judge", _request_id="request-2",
                            output_text=json.dumps({"correctness": 1,
                                "answer_relevance": 1, "abstention": "not_applicable",
                                "reason": "Matches the reference."}),
                            usage=SimpleNamespace(model_dump=lambda: {"input_tokens": 11}))
    grounded = SimpleNamespace(id="response-3", model="judge", _request_id="request-3",
                               output_text=json.dumps({"groundedness": 0.5,
                                   "reason": "One claim lacks retrieved support."}),
                               usage=SimpleNamespace(model_dump=lambda: {"input_tokens": 7}))
    create = Mock(side_effect=[invalid, valid, grounded])
    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    monkeypatch.setattr("src.api.core.clients.openai_client", Mock(return_value=client))

    result, metadata = runner.judge(
        {"kind": "single_paper", "question": "Question?", "reference_answer": "Answer.",
         "reference_evidence": []}, "Answer.", [], "gpt-5-mini", "minimal")

    assert result["correctness"] == 1
    assert result["groundedness"] == 0.5
    assert create.call_count == 3
    assert metadata["reference"]["attempts"] == 2
    assert metadata["reference"]["response_ids"] == ["response-1", "response-2"]
    assert metadata["reference"]["usage"]["input_tokens"] == 21
    assert metadata["grounding"]["response_ids"] == ["response-3"]
    grounding_payload = json.loads(create.call_args_list[-1].kwargs["input"])
    assert "reference_answer" not in grounding_payload
    assert "reference_evidence" not in grounding_payload


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


def test_local_run_checkpoints_both_modes(tmp_path, monkeypatch):
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
                "elapsed_seconds": 0.1, "error": None}

    monkeypatch.setattr(runner, "evaluate_item", fake_evaluate)
    args = SimpleNamespace(dataset=dataset, output_root=tmp_path / "runs", run_id="run-1",
        modes=["vanilla", "hybrid"], limit=None, top_k=5, generation_model="model",
        split="all",
        judge=False, judge_model="judge", judge_reasoning_effort="minimal",
        langfuse=False, concurrency=1)
    output = runner.run(args)
    results = json.loads((output / "results.json").read_text())["results"]
    manifest = json.loads((output / "manifest.json").read_text())
    summary = json.loads((output / "summary.json").read_text())
    assert [row["mode"] for row in results] == ["vanilla", "hybrid"]
    assert manifest["status"] == "complete"
    assert manifest["question_profiles"] == {"single_fact": 1}
    assert summary["vanilla"]["profiles"]["single_fact"]["questions"] == 1
    assert (output / "report.md").exists()
    qdrant.close.assert_called_once()
