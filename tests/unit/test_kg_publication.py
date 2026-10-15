"""Publication policy + actual driver adapter with a transactional in-memory double.

No .env, PostgreSQL, Neo4j server, paid providers or user graph mutations.
"""
from contextlib import contextmanager
from copy import deepcopy
import json
import shlex
import subprocess

import pytest

pytest.importorskip("neo4j_graphrag")

from tests.unit.test_kg_extraction import corpus, records, BUILD, PAPER
from tests.unit.test_kg_review import extract_one
from src.api.kg import publication, review
from src.api.kg.neo4j_store import Neo4jStore


@pytest.fixture
def ready(corpus):
    document = extract_one(corpus)
    for entry in document["entries"]:
        review.set_decision(corpus.directory, entry["record_id"], "approved", reviewer="unit reviewer")
    corpus.row.update(id=BUILD, active_build=BUILD, status="ready")
    corpus.locked = False
    corpus.scope_calls = []

    @contextmanager
    def writer_lock():
        assert not corpus.locked
        corpus.locked = True
        try:
            yield
        finally:
            corpus.locked = False

    def scoped(collection, ids, *, active_only):
        assert corpus.locked
        corpus.scope_calls.append(active_only)
        row = corpus.row
        if row["status"] != "ready" or (active_only and (row["deleted"] or row["active_build"] != BUILD)):
            return []
        return [row] if collection == row["collection"] and ids == [row["id"]] else []
    corpus.catalogue.writer_lock = writer_lock
    corpus.catalogue.scoped_ready_builds = scoped
    return corpus


def payload(ready):
    with ready.catalogue.writer_lock():
        return publication.build_payload(ready.directory, ready.settings, ready.catalogue, ready.reader)


class Result(list):
    def single(self):
        assert len(self) <= 1
        return self[0] if self else None
    def consume(self):
        return None


class Transaction:
    """Models only the adapter's fixed statements, not a general Cypher interpreter."""
    def __init__(self, driver):
        self.driver = driver
        self.state = deepcopy(driver.state)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def commit(self):
        self.driver.state = self.state
    def run(self, query, **params):
        self.driver.calls.append((query, deepcopy(params)))
        if self.driver.fail and self.driver.fail in query:
            raise RuntimeError("Injected Neo4j failure")
        nodes, pubs, corpora, edges = (self.state[k] for k in ("nodes", "publications", "corpora", "edges"))
        if query.startswith("CREATE CONSTRAINT"):
            return Result()
        if query.startswith("MERGE (c:KGCorpus"):
            corpus = corpora.setdefault(params["name"], "")
            return Result([dict(active=corpus)])
        if query.startswith("MATCH (c:KGCorpus") and "RETURN" in query:
            return Result([dict(active=corpora[params["name"]])]) if params["name"] in corpora else Result()
        if query.startswith("MATCH (p:KGPublication {id:") and "RETURN" in query:
            return Result([dict(properties=deepcopy(pubs[params["id"]]))]) if params["id"] in pubs else Result()
        if query.startswith("CREATE (p:KGPublication"):
            pubs[params["id"]] = dict(id=params["id"], graph_name=params["name"], manifest_json=params["manifest"], status="staged")
            return Result()
        if query.startswith("UNWIND $rows AS row MERGE (n:"):
            rows = []
            for node in params["rows"]:
                labels = [node["label"]] + (["KGRecord"] if node["label"] in {"KGEntity", "KGObservation", "KGRelationship"} else [])
                value = nodes.setdefault(node["id"], dict(labels=labels, properties=deepcopy(node["properties"])))
                rows.append(dict(id=node["id"], properties=deepcopy(value["properties"])))
            return Result(rows)
        if query.startswith("UNWIND $rows AS row MATCH (s"):
            count = 0
            for edge in params["rows"]:
                if edge["start"] in nodes.keys() | pubs.keys() and edge["end"] in nodes.keys() | pubs.keys():
                    edges.setdefault(edge["properties"]["id"], deepcopy(edge))
                    count += 1
            return Result([dict(count=count)])
        if query.startswith("MATCH (n) WHERE n.id IN"):
            return Result([dict(id=key, **deepcopy(value)) for key, value in nodes.items()
                if key in params["ids"] or ("KGRecord" in value["labels"] and value["properties"].get("publication_id") == params["publication"])])
        if query.startswith("MATCH (s)-[r]->(o)"):
            pub = params["publication"]
            return Result([deepcopy(edge) for edge in edges.values() if edge["properties"].get("publication_id") == pub
                or nodes.get(edge["start"], {}).get("properties", {}).get("publication_id") == pub
                or nodes.get(edge["end"], {}).get("properties", {}).get("publication_id") == pub
                or edge["start"] == pub or edge["end"] == pub])
        if query.startswith("MATCH (p:KGPublication") and "SET p.status" in query:
            pubs[params["id"]]["status"] = "retired"
            return Result()
        if query.startswith("MATCH (c:KGCorpus") and "SET c.active" in query:
            corpora[params["name"]] = params["id"]
            pubs[params["id"]]["status"] = "active"
            return Result()
        if query.startswith("MATCH (p:KGPublication {graph_name:"):
            return Result([dict(id=p["id"], status=p["status"], manifest=p["manifest_json"])
                for p in pubs.values() if p["graph_name"] == params["name"]])
        raise AssertionError("Unexpected query: " + query)


class Session:
    def __init__(self, driver):
        self.driver = driver
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def begin_transaction(self, **kwargs):
        assert kwargs["timeout"] == 30
        return Transaction(self.driver)


class Driver:
    def __init__(self):
        self.state = dict(nodes={}, edges={}, publications={}, corpora={})
        self.calls, self.options, self.fail = [], [], None
    def session(self, **kwargs):
        self.options.append(kwargs)
        return Session(self)
    def close(self): pass


@pytest.fixture
def backend():
    return Neo4jStore(Driver())


def run(ready, backend=None, action="preview", **kwargs):
    return publication.run(ready.directory, ready.settings, ready.catalogue, ready.reader,
                           action=action, store=backend, **kwargs)


def test_preview_and_payload_are_deterministic_approved_only_with_full_provenance(ready):
    first, second = payload(ready), payload(ready)
    assert first == second
    report = run(ready)
    assert report["database_writes"] == report["model_calls"] == 0
    assert report["counts"]["records"] == 2 and report["counts"]["chunks"] == 1
    assert True in ready.scope_calls and False in ready.scope_calls
    chunk = next(n for n in first["nodes"] if n["label"] == "KGChunk")
    assert chunk["properties"]["chunk_index"] == 0 and chunk["properties"]["point_id"]
    support = [e for e in first["edges"] if e["type"] == "SUPPORTED_BY"]
    assert len(support) == 2 and all(e["properties"]["quote"] in chunk["properties"]["text"] for e in support)
    assert all(n["properties"]["publication_id"] == first["id"] for n in first["nodes"] if n["label"].startswith("KGOb") or n["label"] == "KGEntity")


@pytest.mark.parametrize("field,value", [("active_build", "replacement"), ("deleted", 1),
    ("status", "failed"), ("paper_id", BUILD), ("version", 4), ("collection", "elsewhere"), ("source", "uploads")])
def test_stale_deleted_or_wrong_identity_blocks_before_any_graph_write(ready, backend, field, value):
    ready.row[field] = value
    with pytest.raises(ValueError):
        run(ready, backend, "stage")
    assert backend.driver.calls == []


def test_frozen_artifact_corruption_and_manifest_changes_fail_closed(ready, backend):
    from pathlib import Path
    Path(ready.row["manifest"]["text"]["uri"]).write_text("corrupt")
    with pytest.raises(ValueError, match="integrity"):
        run(ready, backend, "stage")
    assert not backend.driver.calls


def test_changed_manifest_hash_fails_before_graph_writes(ready, backend):
    ready.row["manifest"]["artifact"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="manifest changed"):
        run(ready, backend, "stage")
    assert not backend.driver.calls


def test_missing_manifest_is_an_explicit_source_failure(ready, backend):
    ready.row["manifest"] = None
    with pytest.raises(ValueError, match="manifest changed"):
        run(ready, backend, "stage")
    assert not backend.driver.calls


def test_publication_respects_ingestion_lock_failure(ready, backend):
    @contextmanager
    def locked():
        raise RuntimeError("Another paper ingestion command is running")
        yield
    ready.catalogue.writer_lock = locked
    with pytest.raises(RuntimeError, match="ingestion command"):
        run(ready, backend, "stage")
    assert not backend.driver.calls


def test_source_change_before_neo4j_commit_rolls_back(ready, backend):
    p = payload(ready)
    before = deepcopy(backend.driver.state)
    def changed():
        ready.row["deleted"] = 1
        publication.check_scope(p["plan"], p["papers"], ready.catalogue)
    with ready.catalogue.writer_lock(), pytest.raises(ValueError):
        backend.stage(p, changed)
    assert backend.driver.state == before


def test_stage_verify_activate_idempotence_and_source_immutability(ready, backend):
    from hashlib import sha256
    names = ["plan.json", "review.json", "candidates.json", "checkpoints.sqlite"]
    original = {n:sha256((ready.directory/n).read_bytes()).hexdigest() for n in names}
    staged = run(ready, backend, "stage")
    assert staged["status"] == "staged" and not staged["activated"]
    state = deepcopy(backend.driver.state)
    assert run(ready, backend, "stage")["publication_id"] == staged["publication_id"]
    assert backend.driver.state == state
    assert run(ready, backend, "verify")["verified"] is True
    active = run(ready, backend, "activate")
    assert active["status"] == "active" and active["activated"] is True
    assert run(ready, backend, "activate")["active_publication_id"] == active["publication_id"]
    assert run(ready, backend, "stage")["status"] == "active"  # Cannot demote/rewrite active data.
    assert {n:sha256((ready.directory/n).read_bytes()).hexdigest() for n in names} == original


def test_activation_before_staging_rolls_back(ready, backend):
    with pytest.raises(ValueError, match="stage the exact"):
        run(ready, backend, "activate")
    assert not backend.driver.state["corpora"]


def test_replacement_is_cas_guarded_and_retains_old_graph(ready, backend):
    run(ready, backend, "stage")
    old = run(ready, backend, "activate")["publication_id"]
    old_node_ids = set(backend.driver.state["nodes"])
    document = json.loads((ready.directory/"review.json").read_text())
    review.set_decision(ready.directory, document["entries"][1]["record_id"], "approved", reviewer="another reviewer", notes="Rechecked")
    new = run(ready, backend, "stage")["publication_id"]
    assert new != old
    before = deepcopy(backend.driver.state)
    with pytest.raises(ValueError, match="Active publication changed"):
        run(ready, backend, "activate")
    assert backend.driver.state == before
    assert run(ready, backend, "activate", expect_active=old)["active_publication_id"] == new
    assert backend.driver.state["publications"][old]["status"] == "retired"
    assert old_node_ids <= set(backend.driver.state["nodes"])


def test_failure_during_new_stage_preserves_old_active_graph(ready, backend):
    run(ready, backend, "stage")
    old = run(ready, backend, "activate")["publication_id"]
    document = json.loads((ready.directory/"review.json").read_text())
    review.set_decision(ready.directory, document["entries"][1]["record_id"], "excluded", reviewer="test", reason="unsupported")
    before = deepcopy(backend.driver.state)
    backend.driver.fail = "ON CREATE SET r ="
    with pytest.raises(RuntimeError):
        run(ready, backend, "stage")
    assert backend.driver.state == before
    assert backend.driver.state["corpora"][ready.settings.KG_GRAPH_NAME] == old


@pytest.mark.parametrize("tamper", ["record", "missing_edge", "extra_edge", "missing_node", "pointer"])
def test_graph_drift_blocks_verification_and_activation(ready, backend, tamper):
    run(ready, backend, "stage")
    state = backend.driver.state
    if tamper == "record":
        next(n for n in state["nodes"].values() if "KGRecord" in n["labels"])["properties"]["record_json"] = "corrupt"
    elif tamper == "missing_edge":
        state["edges"].pop(next(iter(state["edges"])))
    elif tamper == "extra_edge":
        edge = deepcopy(next(iter(state["edges"].values())))
        edge["properties"]["id"] = "unexpected"
        state["edges"]["unexpected"] = edge
    elif tamper == "missing_node":
        state["nodes"].pop(next(iter(state["nodes"])))
    else:
        state["corpora"][ready.settings.KG_GRAPH_NAME] = next(iter(state["publications"]))
    before = deepcopy(state)
    with pytest.raises(ValueError): run(ready, backend, "verify")
    with pytest.raises(ValueError): run(ready, backend, "activate")
    assert backend.driver.state == before


def test_excluded_or_unreviewed_records_never_publish_and_empty_fails(ready, backend):
    document = json.loads((ready.directory/"review.json").read_text())
    for e in document["entries"]:
        review.set_decision(ready.directory, e["record_id"], "excluded", reviewer="test", reason="unsupported")
    with pytest.raises(ValueError, match="eligible approved"):
        run(ready, backend, "stage")
    assert not backend.driver.calls


def test_reviewed_export_is_not_trusted_and_review_tampering_is_rejected(ready, backend):
    (ready.directory/"reviewed.json").write_text('{"invented":"not authoritative"}')
    assert run(ready)["counts"]["records"] == 2
    document = json.loads((ready.directory/"review.json").read_text())
    document["entries"][0]["record"]["name"] = "invented"
    (ready.directory/"review.json").write_text(json.dumps(document))
    with pytest.raises(ValueError, match="source records"):
        run(ready, backend, "stage")
    assert not backend.driver.calls


def test_explicit_bounds_and_parameterized_queries(ready, backend):
    ready.settings.KG_PUBLISH_MAX_RECORDS = 1
    with pytest.raises(ValueError, match="KG_PUBLISH_MAX_RECORDS"):
        run(ready)
    ready.settings.KG_PUBLISH_MAX_RECORDS = 10000
    ready.settings.KG_PUBLISH_MAX_BYTES = 1  # Deliberate unit-test override, below validated configuration minimum.
    with pytest.raises(ValueError, match="KG_PUBLISH_MAX_BYTES"):
        run(ready)
    ready.settings.KG_PUBLISH_MAX_BYTES = 10000000
    run(ready, backend, "stage")
    assert all("M22" not in query for query, _ in backend.driver.calls)
    assert any("M22" in str(parameters) for _, parameters in backend.driver.calls)


def test_status_is_read_only_and_does_not_claim_runtime_eligibility(ready, backend):
    run(ready, backend, "stage")
    before = deepcopy(backend.driver.state)
    status = backend.status(ready.settings.KG_GRAPH_NAME)
    assert len(status["publications"]) == 1 and status["catalogue_checked"] is False
    assert status["graph_ready"] is False and status["database_writes"] == 0
    assert backend.driver.state == before


def test_make_publication_commands_preserve_scope_and_replacement_pointer():
    result = subprocess.run(["make", "--no-print-directory", "--dry-run", "kg-activate",
        "KG_DIR=data/my pilot", "KG_REVIEW=my review.json", "KG_GRAPH=other-pilot", "KG_EXPECT_ACTIVE=publication:old"],
        capture_output=True, text=True, check=True)
    args = shlex.split(result.stdout)
    assert args[args.index("--output")+1] == "data/my pilot"
    assert args[args.index("--review")+1] == "my review.json"
    assert args[args.index("--graph-name")+1] == "other-pilot"
    assert args[args.index("--expect-active")+1] == "publication:old"
