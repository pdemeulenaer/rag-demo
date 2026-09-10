from contextlib import closing
import json
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import NAMESPACE_URL, uuid5

import pytest
from qdrant_client import QdrantClient, models as m
from sqlalchemy import text

from src.api.papers.catalogue import Catalogue
from src.api.papers.settings import PaperSettings
from src.api.papers.consistency import activate_verified, active_filter, audit, check_build, expected_ids, import_uploads
from src.api.papers.uploads import process_upload, complete_batch, poll_batches
from src.api.papers.artifacts import ArtifactStore
from src.api.papers.arxiv import Paper


@pytest.fixture
def settings(tmp_path):
    return PaperSettings(_env_file=None, PAPERS_DATABASE_URL="sqlite://", PAPERS_ARTIFACT_DIR=tmp_path,
                         PAPERS_STORAGE_MODE="LOCAL")


@pytest.fixture
def catalogue(settings):
    result = Catalogue(settings.PAPERS_DATABASE_URL)
    result.initialize()
    yield result
    result.close()


@pytest.fixture
def qdrant():
    with closing(QdrantClient(":memory:")) as client:
        client.create_collection("uploads", vectors_config=m.VectorParams(size=3, distance=m.Distance.COSINE))
        yield client


def upload(catalogue, suffix="1"):
    return catalogue.upload("hash" + suffix, {"title": "Upload " + suffix, "file_name": "paper.pdf",
        "file_hash": "hash" + suffix, "authors": [], "version": 1}, "uploads", "test-model", "pipeline" + suffix)


def put(client, build, ids):
    client.upsert("uploads", [m.PointStruct(id=pid, vector=[1., 0., 0.], payload={
        "build_id": build["id"], "paper_id": build["paper_id"], "paper_version": 1, "text": "evidence"}) for pid in ids])


def test_schema_v1_migration_preserves_identity_and_manifest(catalogue, settings):
    paper = Paper("2609.00001", 1, "Star clusters", "", ["Author"], ["astro-ph.GA"], "2026", "2026")
    build_id = catalogue.discover(paper, settings)
    build = catalogue.get_build(build_id)
    catalogue.activate(build, {"chunk_count": 2})
    # Recreate the previous column layout in this isolated SQLite database.
    with catalogue.engine.begin() as connection:
        connection.execute(text("ALTER TABLE papers DROP COLUMN source"))
        connection.execute(text("ALTER TABLE papers RENAME COLUMN source_id TO arxiv_id"))
    catalogue.set_checkpoint("schema_version", "1")
    catalogue.initialize()
    catalogue.initialize()  # Idempotent release step.
    assert catalogue.checkpoint("schema_version") == "2"
    assert catalogue.active(settings)[0]["id"] == build_id
    assert catalogue.get_build(build_id)["manifest"] == {"chunk_count": 2}


def test_exact_ids_detect_same_count_substitution(catalogue, qdrant):
    build = upload(catalogue)
    expected = str(uuid5(NAMESPACE_URL, "expected"))
    wrong = str(uuid5(NAMESPACE_URL, "wrong"))
    put(qdrant, build, [wrong])
    manifest = {"chunk_count": 1, "point_ids": [expected]}
    result = check_build(qdrant, {**build, "manifest": manifest})
    assert result["expected_points"] == result["actual_points"] == 1
    assert result["missing_ids"] == [expected]
    assert result["unexpected_ids"] == [wrong]
    with pytest.raises(ValueError):
        activate_verified(catalogue, qdrant, build, manifest)
    assert catalogue.inventory()[0]["queryable"] is False


def test_audit_missing_active_and_unregistered_does_not_write(catalogue, qdrant):
    build = upload(catalogue)
    pid = str(uuid5(NAMESPACE_URL, "expected"))
    put(qdrant, build, [pid])
    manifest = {"chunk_count": 1, "point_ids": [pid]}
    activate_verified(catalogue, qdrant, build, manifest)
    assert audit(catalogue, qdrant, ["uploads"])["ok"] is True
    qdrant.delete("uploads", m.PointIdsList(points=[pid]))
    extra = str(uuid5(NAMESPACE_URL, "orphan"))
    qdrant.upsert("uploads", [m.PointStruct(id=extra, vector=[1., 0., 0.], payload={"file_name": "other.pdf"})])
    before = catalogue.all_builds()
    result = audit(catalogue, qdrant, ["uploads"])
    assert result["ok"] is False
    assert result["active_builds"][0]["missing_ids"] == [pid]
    assert result["unregistered_points"][0]["point_id"] == extra
    assert catalogue.all_builds() == before
    assert qdrant.count("uploads", exact=True).count == 1


def test_adopt_legacy_vectors_idempotently_without_qdrant_writes(catalogue, qdrant, settings):
    ids = [str(uuid5(NAMESPACE_URL, f"legacy:{i}")) for i in range(2)]
    qdrant.upsert("uploads", [m.PointStruct(id=pid, vector=[1., 0., 0.], payload={
        "file_hash": "hash", "file_name": "thesis.pdf", "file_title": "Thesis", "text": "evidence"}) for pid in ids])
    original = qdrant.retrieve("uploads", ids, with_vectors=True)
    assert import_uploads(catalogue, qdrant, "uploads", "test-model")["imported"] == 1
    assert import_uploads(catalogue, qdrant, "uploads", "test-model")["imported"] == 0
    assert qdrant.retrieve("uploads", ids, with_vectors=True) == original
    settings.EMBEDDING_MODEL = "test-model"
    active = catalogue.active(settings, "uploads", "uploads")
    assert len(active) == 1
    assert set(expected_ids(active[0])) == set(ids)
    assert qdrant.count("uploads", count_filter=active_filter(active), exact=True).count == 2
    assert audit(catalogue, qdrant, ["uploads"])["ok"] is True


def test_failed_new_build_preserves_previous_ready_revision(catalogue, qdrant):
    old = upload(catalogue)
    pid = str(uuid5(NAMESPACE_URL, "first"))
    put(qdrant, old, [pid])
    activate_verified(catalogue, qdrant, old, {"chunk_count": 1, "point_ids": [pid]})
    replacement = catalogue.upload("hash1", old["metadata"], "uploads", "test-model", "new-pipeline")
    catalogue.start(replacement["id"])
    catalogue.fail(replacement["id"], "test")
    inventory = catalogue.inventory("uploads")
    assert len(inventory) == 1
    assert inventory[0]["status"] == "failed"
    assert inventory[0]["queryable"] is True
    assert inventory[0]["active_build"] == old["id"]


def process_args(catalogue, qdrant, settings, tmp_path, mode="sync"):
    path = tmp_path / "paper.pdf"
    path.write_bytes(b"%PDF-fixture")
    digest = sha256(path.read_bytes()).hexdigest()
    build = catalogue.upload(digest, {"file_hash": digest, "file_name": "paper.pdf", "title": "paper.pdf", "version": 1},
                             "uploads", "test-model", "pipeline")
    image = {"bytes": b"image-fixture", "filename": "figure.jpg", "page_number": 2, "caption": "A star cluster"}
    extract = Mock(return_value=([("Paper evidence", 1)], [image], "First page", {}))
    metadata = Mock(return_value=SimpleNamespace(title="Scientific paper", authors=["Author"],
        keywords=["star cluster"], publication_year="2026", summary="Summary"))
    openai = Mock()
    openai.files.create.return_value.id = "file-fixture"
    openai.batches.create.return_value.id = "batch-fixture"
    embed = Mock(side_effect=lambda texts: [[1., 0., 0.] for _ in texts])
    return dict(catalogue=catalogue, qdrant=qdrant, build=build, path=path, mode=mode,
        store=ArtifactStore(settings), extract=extract, metadata=metadata, describe=Mock(return_value="Scientific figure"),
        embed=embed, storage=Mock(), openai_client=openai,
        template={"system": "Describe", "user": SimpleNamespace(render=lambda **kw: "Figure"), "model": "test-model"})


def test_sync_upload_activates_only_complete_manifest(catalogue, qdrant, settings, tmp_path):
    args = process_args(catalogue, qdrant, settings, tmp_path)
    process_upload(**args)
    build = catalogue.get_build(args["build"]["id"])
    assert build["status"] == "ready"
    assert build["manifest"]["chunk_count"] == 3  # text + summary + figure
    assert check_build(qdrant, build)["ok"] is True
    figure = next(p for p in qdrant.retrieve("uploads", expected_ids(build)) if p.payload["type"] == "figure")
    assert figure.payload["page_number"] == 2
    assert figure.payload["caption"] == "A star cluster"
    assert catalogue.inventory()[0]["title"] == "Scientific paper"


@pytest.mark.parametrize("failure", ["storage", "describe", "embed"])
def test_sync_failure_never_marks_ready(catalogue, qdrant, settings, tmp_path, failure):
    args = process_args(catalogue, qdrant, settings, tmp_path)
    if failure == "storage":
        args["storage"].save_image.side_effect = RuntimeError("failed")
    else:
        args[failure].side_effect = RuntimeError("failed")
    with pytest.raises(RuntimeError):
        process_upload(**args)
    assert catalogue.get_build(args["build"]["id"])["status"] == "failed"
    assert catalogue.inventory()[0]["queryable"] is False


def test_batch_upload_keeps_text_hidden_until_all_figures_verify(catalogue, qdrant, settings, tmp_path):
    args = process_args(catalogue, qdrant, settings, tmp_path, mode="batch")
    process_upload(**args)
    build = catalogue.get_build(args["build"]["id"])
    assert build["status"] == "waiting_batch"
    assert catalogue.inventory()[0]["queryable"] is False
    assert qdrant.count("uploads", exact=True).count == 2
    key = next(iter(build["manifest"]["figure_tasks"]))
    output = json.dumps({"custom_id": key, "response": {"status_code": 200,
        "body": {"choices": [{"message": {"content": "Figure explanation"}}]}}})
    complete_batch(catalogue, qdrant, build, output, args["embed"])
    assert catalogue.get_build(build["id"])["status"] == "ready"
    assert qdrant.count("uploads", exact=True).count == 3
    # Replay cannot duplicate points.
    complete_batch(catalogue, qdrant, build, output, args["embed"])
    assert qdrant.count("uploads", exact=True).count == 3


def test_batch_missing_results_and_terminal_failure(catalogue, qdrant, settings, tmp_path):
    args = process_args(catalogue, qdrant, settings, tmp_path, mode="batch")
    process_upload(**args)
    build = catalogue.get_build(args["build"]["id"])
    with pytest.raises(ValueError, match="missing"):
        complete_batch(catalogue, qdrant, build, "", args["embed"])
    assert catalogue.inventory()[0]["queryable"] is False
    client = Mock()
    client.batches.retrieve.return_value.status = "expired"
    poll_batches(catalogue, qdrant, client, args["embed"])
    assert catalogue.get_build(build["id"])["status"] == "failed"


def test_retained_builds_are_not_orphans(catalogue, qdrant):
    old = upload(catalogue)
    pid = str(uuid5(NAMESPACE_URL, "old"))
    put(qdrant, old, [pid])
    activate_verified(catalogue, qdrant, old, {"chunk_count": 1, "point_ids": [pid]})
    new = catalogue.upload("hash1", old["metadata"], "uploads", "test-model", "replacement")
    new_pid = str(uuid5(NAMESPACE_URL, "new"))
    put(qdrant, new, [new_pid])
    activate_verified(catalogue, qdrant, new, {"chunk_count": 1, "point_ids": [new_pid]})
    result = audit(catalogue, qdrant, ["uploads"])
    assert result["ok"] is True
    assert result["retained_builds"] == [old["id"]]
