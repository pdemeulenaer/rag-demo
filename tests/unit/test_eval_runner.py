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
        {"reference_evidence": [{"point_id": "gold"}, {"point_id": "missed"}]},
        [{"id": "gold"}, {"id": "other"}], ["gold"])
    assert metrics["retrieval_hit"] == 1.0
    assert metrics["retrieval_recall"] == 0.5
    assert metrics["gold_citation_recall"] == 0.5
    assert metrics["citation_from_retrieval"] == 1.0


def test_judge_retries_one_invalid_structured_response(monkeypatch):
    invalid = SimpleNamespace(id="response-1", model="judge", output_text="{}",
                              usage=SimpleNamespace(model_dump=lambda: {"input_tokens": 10}))
    valid = SimpleNamespace(id="response-2", model="judge", _request_id="request-2",
                            output_text=json.dumps({"correctness": 1, "groundedness": 1,
                                "answer_relevance": 1, "abstention": "not_applicable",
                                "reason": "Supported."}),
                            usage=SimpleNamespace(model_dump=lambda: {"input_tokens": 11}))
    create = Mock(side_effect=[invalid, valid])
    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    monkeypatch.setattr("src.api.core.clients.openai_client", Mock(return_value=client))

    result, metadata = runner.judge(
        {"kind": "single_paper", "question": "Question?", "reference_answer": "Answer.",
         "reference_evidence": []}, "Answer.", [], "gpt-5-mini", "minimal")

    assert result["correctness"] == 1
    assert create.call_count == 2
    assert metadata["attempts"] == 2
    assert metadata["response_ids"] == ["response-1", "response-2"]
    assert metadata["usage"]["input_tokens"] == 21


def test_local_run_checkpoints_both_modes(tmp_path, monkeypatch):
    dataset = reviewed_dataset(tmp_path / "dataset")
    qdrant = Mock()
    monkeypatch.setattr(runner, "QdrantClient", Mock(return_value=qdrant))

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
