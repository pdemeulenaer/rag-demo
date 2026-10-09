import json
import stat

import pytest

from evals import review_dataset as review


def snapshot():
    papers = []
    evidence = []
    for number in range(1, 5):
        papers.append({
            "paper_id": f"paper-{number}",
            "build_id": f"build-{number}",
            "collection": "papers",
            "embedding_model": "embedding-model",
        })
        evidence.append({
            "evidence_id": f"evidence-{number}",
            "point_id": f"point-{number}",
            "paper_id": f"paper-{number}",
            "build_id": f"build-{number}",
        })
    return {
        "schema_version": 1,
        "active_build_ids": [f"build-{number}" for number in range(1, 5)],
        "papers": papers,
        "evidence": evidence,
    }


def evidence(number):
    return [{
        "evidence_id": f"evidence-{number}",
        "point_id": f"point-{number}",
        "paper_id": f"paper-{number}",
        "build_id": f"build-{number}",
    }]


def metadata(*, corpus=False):
    return {
        "reviewer": "reviewer-1",
        "reviewed_at": "2026-09-15T12:00:00Z",
        "decision": "approved",
        "original_sources_checked": True,
        "corpus_search_verified": corpus,
    }


def question(question_id, kind, numbers, *, unanswerable=False):
    references = [] if unanswerable else [item for number in numbers for item in evidence(number)]
    return {
        "id": question_id,
        "kind": kind,
        "question": f"Question {question_id}?",
        "reference_answer": "The frozen corpus does not provide that information."
        if unanswerable else "A reviewed answer.",
        "review_status": "approved",
        "answerability_scope": "frozen_corpus" if unanswerable else "supplied_excerpts_only",
        "reference_evidence": references,
        "generation_evidence_ids": [f"evidence-{number}" for number in numbers],
        "review": metadata(corpus=unanswerable),
    }


def dataset():
    frozen = snapshot()
    return frozen, {
        "schema_version": 2,
        "snapshot_hash": review.canonical_hash(frozen),
        "plan_hash": "plan-hash",
        "questions": [
            question("q1", "single_paper", [1]),
            question("q2", "unanswerable_candidate", [1], unanswerable=True),
            question("q3", "cross_paper", [2, 3]),
            question("q4", "single_paper", [4]),
            question("q5", "single_paper", [2]),
        ],
    }


def test_assign_splits_keeps_connected_papers_together_and_validates():
    frozen, reviewed = dataset()
    result = review.assign_splits(reviewed, frozen, test_ratio=0.25, seed=42)

    approved = result["questions"]
    assert {row["split"] for row in approved} == {"development", "test"}
    assert result["split_policy"]["development_questions"] + result["split_policy"]["test_questions"] == 5
    q1 = next(row for row in approved if row["id"] == "q1")
    q2 = next(row for row in approved if row["id"] == "q2")
    assert (q1["group_id"], q1["split"]) == (q2["group_id"], q2["split"])
    normalized, selected = review.validate_v2(result, frozen, selected_split="test")
    assert normalized["schema_version"] == 2
    assert selected
    assert all(row["split"] == "test" for row in selected)


def test_approved_unanswerable_requires_full_corpus_verification():
    frozen, reviewed = dataset()
    reviewed["questions"][1]["answerability_scope"] = "supplied_excerpts_only"

    with pytest.raises(review.ReviewDatasetError, match="frozen_corpus scope"):
        review.validate_v2(reviewed, frozen, require_splits=False)


def test_profile_must_match_question_kind():
    frozen, reviewed = dataset()
    reviewed["questions"][0]["profile"] = "cross_multihop"
    with pytest.raises(review.ReviewDatasetError, match="profile does not match"):
        review.validate_v2(reviewed, frozen, require_splits=False)


def test_cross_paper_group_cannot_leak_across_splits():
    frozen, reviewed = dataset()
    result = review.assign_splits(reviewed, frozen, test_ratio=0.25, seed=42)
    cross = next(row for row in result["questions"] if row["id"] == "q3")
    cross["split"] = "test" if cross["split"] == "development" else "development"

    with pytest.raises(review.ReviewDatasetError, match="invalid paper-component group_id|leaks"):
        review.validate_v2(result, frozen)


def test_split_policy_counts_must_match_assignments():
    frozen, reviewed = dataset()
    result = review.assign_splits(reviewed, frozen, test_ratio=0.25, seed=42)
    result["split_policy"]["test_questions"] += 1

    with pytest.raises(review.ReviewDatasetError, match="counts do not match"):
        review.validate_v2(result, frozen)


def test_load_files_checks_snapshot_hash(tmp_path):
    frozen, reviewed = dataset()
    (tmp_path / "snapshot.json").write_text(json.dumps(frozen))
    path = tmp_path / "questions.reviewed.json"
    path.write_text(json.dumps(reviewed))
    review.load_files(path)

    frozen["active_build_ids"].append("changed")
    (tmp_path / "snapshot.json").write_text(json.dumps(frozen))
    with pytest.raises(review.ReviewDatasetError, match="do not match"):
        review.load_files(path)


def test_split_output_is_private_and_never_overwritten(tmp_path):
    path = tmp_path / "questions.split.json"
    review.write_json(path, {"first": True})
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    with pytest.raises(review.ReviewDatasetError, match="already exists"):
        review.write_json(path, {"first": False})
    assert json.loads(path.read_text()) == {"first": True}
