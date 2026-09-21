"""Offline evaluation rebase tests; no databases, network, or model calls."""
from contextlib import closing
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

import pytest
from qdrant_client import QdrantClient, models as m

from evals import rebase_dataset as rebase
from evals.review_dataset import canonical_hash, validate_v2
from src.api.rag.sparse import ensure_hybrid_collection, point_vectors


class FakeCatalogue:
    def __init__(self, old_build, new_build):
        self.old_build = old_build
        self.new_build = new_build

    def require_schema(self):
        return None

    def active(self, settings, source="arxiv", collection=None):
        return [self.new_build]

    def get_build(self, build_id):
        return self.old_build if build_id == self.old_build["id"] else None


def fixture(tmp_path: Path, *, changed=False):
    old_id = str(uuid5(NAMESPACE_URL, "old-point"))
    new_id = str(uuid5(NAMESPACE_URL, "new-point"))
    paper_id = "paper-1"
    old_build = {
        "id": "old-build", "paper_id": paper_id, "version": 1,
        "collection": "papers-v1", "embedding_model": "embedding-model",
        "metadata": {"title": "Star clusters", "abstract": "Mass measurements",
                     "authors": ["A. Author"], "published": "2026-01-01",
                     "categories": ["astro-ph.GA"]},
        "status": "ready", "manifest": {"chunk_count": 1, "point_ids": [old_id]},
    }
    new_build = {
        **old_build,
        "id": "new-build", "collection": "papers-v2",
        "manifest": {"chunk_count": 1, "point_ids": [new_id],
                     "retrieval_index": {"sparse_vector_name": "bm25"}},
        "source": "arxiv",
    }
    old_text = "The measured star-cluster mass is one million solar masses."
    new_text = old_text if not changed else "The revised mass is two million solar masses."
    old_payload = {
        "type": "text", "text": old_text, "chunk_index": 0, "page_number": 3,
        "section_header": "Results", "content_kind": "text",
        "build_id": old_build["id"], "paper_id": paper_id, "paper_version": 1,
    }
    new_payload = {
        **old_payload, "text": new_text, "build_id": new_build["id"],
    }
    client = QdrantClient(":memory:")
    client.create_collection(
        "papers-v1", vectors_config=m.VectorParams(size=2, distance=m.Distance.COSINE)
    )
    ensure_hybrid_collection(client, "papers-v2", 2)
    client.upsert("papers-v1", [m.PointStruct(
        id=old_id, vector=[1.0, 0.0], payload=old_payload,
    )])
    client.upsert("papers-v2", [m.PointStruct(
        id=new_id, vector=point_vectors([1.0, 0.0], new_text), payload=new_payload,
    )])
    evidence = {
        "evidence_id": "stable-evidence", "point_id": old_id,
        "collection": "papers-v1", "paper_id": paper_id,
        "build_id": old_build["id"], "version": 1, "source": "arxiv",
        "title": "Star clusters", "page_number": 3, "text": old_text,
        "section_header": "Results", "content_kind": "text",
    }
    snapshot = {
        "schema_version": 1, "created_at": "2026-01-01T00:00:00Z",
        "source": "arxiv", "scope_id": "old-scope", "corpus_fingerprint": "old",
        "active_build_ids": [old_build["id"]], "excluded_no_text_build_ids": [],
        "seed": 42,
        "papers": [{
            "paper_id": paper_id, "build_id": old_build["id"], "source": "arxiv",
            "collection": "papers-v1", "version": 1,
            "embedding_model": "embedding-model", "title": "Star clusters",
            "abstract": "Mass measurements", "authors": ["A. Author"], "year": "2026",
            "categories": ["astro-ph.GA"], "evidence_ids": ["stable-evidence"],
        }],
        "evidence": [evidence],
    }
    reviewed = {
        "schema_version": 2, "snapshot_hash": canonical_hash(snapshot),
        "plan_hash": "old-plan", "split_policy": None,
        "questions": [{
            "id": "q0001", "kind": "single_paper", "profile": "single_fact",
            "question": "What mass was measured?", "reference_answer": "One million.",
            "review_status": "approved", "answerability_scope": "supplied_excerpts_only",
            "reference_evidence": [evidence],
            "generation_evidence_ids": ["stable-evidence"], "paper_ids": [paper_id],
            "review": {"reviewer": "reviewer", "reviewed_at": "2026-01-02T00:00:00Z",
                       "decision": "approved", "original_sources_checked": True},
        }],
    }
    source = tmp_path / "source" / "questions.split.json"
    source.parent.mkdir()
    (source.parent / "snapshot.json").write_text(json.dumps(snapshot))
    source.write_text(json.dumps(reviewed))
    settings = SimpleNamespace(scope_id="new-scope")
    options = SimpleNamespace(QDRANT_COLLECTION_NAME="uploads-v2")
    return source, client, FakeCatalogue(old_build, new_build), settings, options


def test_rebase_preserves_approval_only_for_identical_complete_text(tmp_path):
    source, client, catalogue, settings, options = fixture(tmp_path)
    original = source.read_bytes()
    output = tmp_path / "rebased"
    try:
        result = rebase.run(source, output, catalogue=catalogue, client=client,
                            settings=settings, options=options)
    finally:
        client.close()

    assert source.read_bytes() == original
    assert result["approved_retained"] == 1
    reviewed = json.loads((output / "questions.reviewed.json").read_text())
    snapshot = json.loads((output / "snapshot.json").read_text())
    question = reviewed["questions"][0]
    assert question["review_status"] == "approved"
    assert question["rebase_status"] == "exact"
    assert question["reference_evidence"][0]["build_id"] == "new-build"
    assert question["reference_evidence"][0]["collection"] == "papers-v2"
    assert question["reference_evidence"][0]["evidence_id"] == "stable-evidence"
    assert snapshot["active_build_ids"] == ["new-build"]
    validate_v2(reviewed, snapshot, require_splits=False)


def test_rebase_downgrades_approval_when_text_stream_changed(tmp_path):
    source, client, catalogue, settings, options = fixture(tmp_path, changed=True)
    try:
        result = rebase.run(source, tmp_path / "rebased", catalogue=catalogue,
                            client=client, settings=settings, options=options)
    finally:
        client.close()

    assert result["approved_retained"] == 0
    assert result["approved_downgraded"] == 1
    question = json.loads(
        (tmp_path / "rebased" / "questions.reviewed.json").read_text()
    )["questions"][0]
    assert question["review_status"] == "needs_review"
    assert question["review"] is None
    assert question["previous_review"]["decision"] == "approved"
    assert question["rebase_unmatched_evidence_ids"] == ["stable-evidence"]


def test_rebase_never_overwrites_output_directory(tmp_path):
    source, client, catalogue, settings, options = fixture(tmp_path)
    output = tmp_path / "rebased"
    output.mkdir()
    try:
        with pytest.raises(rebase.RebaseError, match="already exists"):
            rebase.run(source, output, catalogue=catalogue, client=client,
                       settings=settings, options=options)
    finally:
        client.close()
