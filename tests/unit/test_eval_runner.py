import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from evals import run_benchmark as runner


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
            {"id": "q1", "kind": "single_paper", "question": "What happened?",
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


def test_deterministic_metrics_uses_qdrant_point_ids():
    metrics = runner.deterministic_metrics(
        {"reference_evidence": [{"point_id": "gold"}, {"point_id": "missed"}]},
        [{"id": "gold"}, {"id": "other"}], ["gold"])
    assert metrics["retrieval_hit"] == 1.0
    assert metrics["retrieval_recall"] == 0.5
    assert metrics["gold_citation_recall"] == 0.5
    assert metrics["citation_from_retrieval"] == 1.0


def test_local_run_checkpoints_both_modes(tmp_path, monkeypatch):
    dataset = reviewed_dataset(tmp_path / "dataset")
    qdrant = Mock()
    monkeypatch.setattr(runner, "QdrantClient", Mock(return_value=qdrant))

    def fake_evaluate(question, mode, **kwargs):
        return {"question_id": question["id"], "kind": question["kind"], "mode": mode,
                "question": question["question"], "reference_answer": question["reference_answer"],
                "answer": mode, "retrieved_chunks": [], "cited_context_ids": [],
                "metrics": {"retrieval_recall": 1.0}, "judge": None, "judge_request": None,
                "elapsed_seconds": 0.1, "error": None}

    monkeypatch.setattr(runner, "evaluate_item", fake_evaluate)
    args = SimpleNamespace(dataset=dataset, output_root=tmp_path / "runs", run_id="run-1",
        modes=["vanilla", "hybrid"], limit=None, top_k=5, generation_model="model",
        judge=False, judge_model="judge", judge_reasoning_effort="minimal",
        langfuse=False, concurrency=1)
    output = runner.run(args)
    results = json.loads((output / "results.json").read_text())["results"]
    manifest = json.loads((output / "manifest.json").read_text())
    assert [row["mode"] for row in results] == ["vanilla", "hybrid"]
    assert manifest["status"] == "complete"
    assert (output / "report.md").exists()
    qdrant.close.assert_called_once()
