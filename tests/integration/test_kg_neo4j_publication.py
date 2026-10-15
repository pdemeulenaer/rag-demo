"""Opt-in real Neo4j tests, using ONLY a disposable, randomly named container.

KG_RUN_NEO4J_INTEGRATION=1 .venv/bin/python -m pytest tests/integration/test_kg_neo4j_publication.py -q
Requires the pinned image already present; never pulls images or uses .env/Compose.
"""
import os
import subprocess
import time
from uuid import uuid4

import pytest

pytest.importorskip("neo4j")
from neo4j import GraphDatabase

from tests.unit.test_kg_publication import ready, payload, run
from tests.unit.test_kg_extraction import corpus as base_corpus
from src.api.kg.neo4j_store import Neo4jStore
from src.api.kg import review
import json

pytestmark = pytest.mark.skipif(os.environ.get("KG_RUN_NEO4J_INTEGRATION") != "1",
                               reason="Opt-in disposable Neo4j container test")


@pytest.fixture(scope="module")
def immutable_artifacts(tmp_path_factory):
    return tmp_path_factory.mktemp("kg-native-artifacts")


@pytest.fixture
def corpus(tmp_path, immutable_artifacts):
    # Shared source IDs must refer to identical immutable manifests across cases.
    # Only extraction/review checkpoint directories are separate per test.
    result = base_corpus.__wrapped__(immutable_artifacts)
    result.directory = tmp_path / "kg"
    return result


@pytest.fixture(scope="module")
def native_driver():
    name = "rag-demo-kg-test-" + uuid4().hex
    started = False
    driver = None
    try:
        subprocess.run(["docker", "run", "--pull=never", "--rm", "-d", "--name", name,
            "--label", "rag-demo.kg-integration=true", "--memory=1g", "-p", "127.0.0.1::7687",
            "-e", "NEO4J_AUTH=neo4j/kg-integration-only",
            "-e", "NEO4J_server_memory_heap_initial__size=128m",
            "-e", "NEO4J_server_memory_heap_max__size=256m",
            "-e", "NEO4J_server_memory_pagecache_size=128m", "neo4j:2026.09.0"],
            check=True, capture_output=True, text=True)
        started = True
        address = subprocess.check_output(["docker", "port", name, "7687/tcp"], text=True).strip()
        driver = GraphDatabase.driver("bolt://" + address, auth=("neo4j", "kg-integration-only"),
                                      connection_timeout=2, max_transaction_retry_time=0)
        deadline = time.monotonic() + 60
        while True:
            try:
                driver.verify_connectivity()
                break
            except Exception:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)
        yield driver
    finally:
        if driver:
            driver.close()
        if started:
            subprocess.run(["docker", "stop", "-t", "5", name], check=True, capture_output=True)


@pytest.fixture
def native(ready, native_driver):
    ready.settings.KG_GRAPH_NAME = "integration-" + uuid4().hex
    return Neo4jStore(native_driver)


def test_native_stage_verify_activation_replacement_and_retention(ready, native):
    first = run(ready, native, "stage")
    assert first["status"] == "staged"
    assert run(ready, native, "stage")["publication_id"] == first["publication_id"]
    assert run(ready, native, "verify")["verified"]
    active = run(ready, native, "activate")
    old = active["publication_id"]
    assert run(ready, native, "activate")["active_publication_id"] == old
    document = json.loads((ready.directory/"review.json").read_text())
    review.set_decision(ready.directory, document["entries"][1]["record_id"], "approved",
                        reviewer="native integration", notes="Reviewed again")
    new = run(ready, native, "stage")["publication_id"]
    with pytest.raises(ValueError, match="Active publication changed"):
        run(ready, native, "activate")
    assert native.status(ready.settings.KG_GRAPH_NAME)["active_publication_id"] == old
    assert run(ready, native, "activate", expect_active=old)["active_publication_id"] == new
    history = native.status(ready.settings.KG_GRAPH_NAME)["publications"]
    assert {p["publication_id"]:p["status"] for p in history} == {old:"retired",new:"active"}


def test_native_rollback_on_final_scope_failure(ready, native):
    p = payload(ready)
    def fail():
        raise ValueError("Source eligibility changed before commit")
    with pytest.raises(ValueError, match="Source eligibility"):
        native.stage(p, fail)
    assert native.status(ready.settings.KG_GRAPH_NAME)["publications"] == []


def test_native_content_tampering_blocks_activation(ready, native):
    p = payload(ready)
    run(ready, native, "stage")
    with native.transaction() as tx:
        tx.run("MATCH (n:KGRecord {publication_id: $id}) SET n.record_json = 'tampered'", id=p["id"]).consume()
    with pytest.raises(ValueError, match="node content"):
        run(ready, native, "verify")
    with pytest.raises(ValueError, match="node content"):
        run(ready, native, "activate")
    assert native.status(ready.settings.KG_GRAPH_NAME)["active_publication_id"] is None


def test_native_read_only_scoped_traversal_and_retired_exclusion(ready,native):
    from src.api.kg.retrieval import KGReader, KGUnavailable
    from src.api.rag.contracts import RetrievalScope, ScopedBuild
    p=payload(ready)
    reader=KGReader(native.driver,ready.settings)
    run(ready,native,"stage")
    with pytest.raises(KGUnavailable,match="no_active"):
        reader.publication()
    run(ready,native,"activate")
    build=p["papers"][0]
    scope=RetrievalScope(build["collection"],(build["build_id"],),
        builds=(ScopedBuild(build["build_id"],build["paper_id"]),))
    name=next(n["properties"]["name"] for n in p["nodes"] if n["label"]=="KGEntity")
    with ready.catalogue.writer_lock():  # Fixture checks its SQL reads occur within this context.
        result=reader.search(name,scope=scope,catalogue=ready.catalogue,seeds=[],limit=5)
    assert result.diagnostics["eligible_graph_paper_count"] == 1
    assert result.diagnostics["validated_record_count"] > 0
    assert result.diagnostics["matched_entity_ids"]
    assert result.chunks
    assert result.diagnostics["publication_id"] == p["id"]
    assert result.chunks[0].build_id == build["build_id"]
    # Read query must not alter the staged/active projection, including source links.
    assert run(ready,native,"verify")["verified"]
    ready.row["deleted"]=True
    with ready.catalogue.writer_lock():
        result=reader.search(name,scope=scope,catalogue=ready.catalogue,seeds=[],limit=5)
    assert result.chunks == [] and result.diagnostics["eligible_graph_paper_count"] == 0
    ready.row["deleted"]=False
    document=json.loads((ready.directory/"review.json").read_text())
    review.set_decision(ready.directory,document["entries"][0]["record_id"],"approved",
                        reviewer="native integration",notes="Publication replacement")
    run(ready,native,"stage")
    run(ready,native,"activate",expect_active=p["id"])
    with pytest.raises(KGUnavailable,match="publication_changed"):
        reader.publication(p["id"])
    with ready.catalogue.writer_lock():
        current=reader.search(name,scope=scope,catalogue=ready.catalogue,seeds=[],limit=5)
    assert current.chunks and current.diagnostics["publication_id"] != p["id"]
