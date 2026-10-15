"""Offline record quarantine/review: no .env, providers or graph writes."""
from copy import deepcopy
import json
import sqlite3

import pytest
from pydantic import ValidationError

pytest.importorskip("neo4j_graphrag")

from tests.unit.test_kg_extraction import corpus, prepare, records, sdk_component, PAPER, BUILD
from src.api.kg import jobs, review
from src.api.kg.__main__ import main
from src.api.kg.extraction import CandidateRecords, bind_sources, quarantine_report, staging_graph
from src.api.kg.record_schema import ExtractionBatch
from src.api.kg.artifacts import load_paper


def extract_one(corpus, body=None):
    prepare(corpus)
    component, requests, client = sdk_component(corpus.settings, [body or records()])
    try:
        result = jobs.extract(corpus.directory, corpus.settings, max_calls=1, component=component)
        assert result["states"]["complete"] == 1 and len(requests) == 1
    finally:
        client.close()
    review.prepare(corpus.directory)
    return json.loads((corpus.directory / "review.json").read_text())


def test_orphan_observation_and_dependent_edge_are_held_with_valid_siblings(corpus):
    body = records()
    bad = deepcopy(body["observations"][0])
    bad.update(id="orphan", subject_id="absent")
    body["observations"].append(bad)
    body["relationships"] = [dict(id="edge", subject_id="distance", object_id="orphan",
        predicate="compares_with", epistemic_status="reported", evidence=[dict(span_id="s001")])]
    document = extract_one(corpus, body)
    byid = {e["record_id"].split(":")[-1]: e for e in document["entries"]}
    assert byid["orphan"]["quarantine_reasons"] == ["undeclared_observation_subject"]
    assert byid["edge"]["quarantine_reasons"] == ["quarantined_endpoint"]
    assert byid["orphan"]["record"]["subject_id"].endswith(":absent")
    saved = json.loads((corpus.directory / "candidates.json").read_text())["chunks"][0]
    assert len(saved["batch"]["observations"]) == 2 and len(saved["graph"]["nodes"]) == 2
    assert saved["quarantine"][0]["paths"] == ["observations.1.subject_id"]
    assert jobs.validate(corpus.directory)["quarantined_records"] == 2


@pytest.mark.parametrize("failure", ["missing_endpoint", "wrong_role"])
def test_invalid_edge_keeps_both_valid_nodes_and_observation(corpus, failure):
    body = records()
    body["relationships"] = [dict(id="edge", subject_id="distance", object_id="absent" if failure == "missing_endpoint" else "m22",
        predicate="proposes_origin", epistemic_status="hypothesis", evidence=[dict(span_id="s001")])]
    document = extract_one(corpus, body)
    held = [e for e in document["entries"] if e["quarantine_reasons"]]
    assert len(held) == 1 and held[0]["record_type"] == "relationship"
    assert "invalid_relationship_role" in held[0]["quarantine_reasons"]
    assert review.validate(corpus.directory)["eligible_records"] == 0  # No automatic approvals.


@pytest.mark.parametrize("failure", ["duplicate", "wrong_build", "wrong_quote", "wrong_point"])
def test_corrupt_identity_or_provenance_remains_chunk_wide_failure(corpus, failure):
    source = load_paper(corpus.paper, corpus.catalogue, corpus.reader)[0][0]
    batch = bind_sources(CandidateRecords.model_validate(records()), source, corpus.settings.KG_MODEL)
    raw = batch.model_dump(mode="json")
    if failure == "duplicate":
        raw["observations"][0]["id"] = raw["entities"][0]["id"]
    elif failure == "wrong_build":
        raw["observations"][0]["evidence"][0]["build_id"] = PAPER
    elif failure == "wrong_quote":
        raw["observations"][0]["evidence"][0]["quote"] = "invented quote"
    else:
        raw["observations"][0]["evidence"][0]["point_id"] = BUILD
    with pytest.raises(ValueError):
        ExtractionBatch.model_validate(raw).validate_sources([source])


def test_prepare_idempotent_and_unreviewed_export_empty(corpus):
    document = extract_one(corpus)
    assert all(e["decision"] == "needs_review" for e in document["entries"])
    before = (corpus.directory / "review.json").read_bytes()
    database_before = (corpus.directory / "checkpoints.sqlite").read_bytes()
    review.prepare(corpus.directory)
    assert (corpus.directory / "review.json").read_bytes() == before
    result = review.validate(corpus.directory, export=True)
    assert result["eligible_records"] == 0 and result["graph_ready"] is False
    exported = json.loads((corpus.directory / "reviewed.json").read_text())
    assert exported["chunks"][0]["graph"]["nodes"] == []
    assert (corpus.directory / "checkpoints.sqlite").read_bytes() == database_before


def test_explicit_presentation_exclusion_preserves_source_and_surviving_records(corpus):
    body = records()
    legend = deepcopy(body["observations"][0])
    legend.update(id="legend", kind="qualitative_finding", statement="Black circles denote members.",
                  quantity=None, value_text=None, unit_text=None, uncertainty_text=None)
    body["observations"].append(legend)
    document = extract_one(corpus, body)
    raw_before = (corpus.directory / "candidates.json").read_bytes()
    for entry in document["entries"]:
        excluded = entry["record_id"].endswith(":legend")
        review.set_decision(corpus.directory, entry["record_id"], "excluded" if excluded else "approved",
            reviewer="test reviewer", reason="presentation_only" if excluded else None)
    result = review.validate(corpus.directory, export=True)
    assert result["review_complete"] and result["eligible_records"] == 2
    assert result["decisions"] == {"approved": 2, "excluded": 1}
    exported = json.loads((corpus.directory / "reviewed.json").read_text())
    assert all(not node["id"].endswith(":legend") for node in exported["chunks"][0]["graph"]["nodes"])
    assert (corpus.directory / "candidates.json").read_bytes() == raw_before


def test_approved_observation_waits_for_subject_approval(corpus):
    document = extract_one(corpus)
    entity, observation = document["entries"]
    review.set_decision(corpus.directory, observation["record_id"], "approved", reviewer="test")
    result = review.validate(corpus.directory)
    assert result["eligible_records"] == 0
    assert result["approved_but_dependency_held"] == [observation["record_id"]]
    review.set_decision(corpus.directory, entity["record_id"], "approved", reviewer="test")
    assert review.validate(corpus.directory)["eligible_records"] == 2
    review.set_decision(corpus.directory, entity["record_id"], "excluded", reviewer="test", reason="unsupported")
    assert review.validate(corpus.directory)["eligible_records"] == 0


@pytest.mark.parametrize("failure", ["approve_held", "approve_without_reviewer", "exclude_without_reason"])
def test_review_decision_cannot_bypass_guards_or_attribution(corpus, failure):
    body = records()
    body["observations"][0]["quality_flags"] = ["ambiguous_source_units"]
    document = extract_one(corpus, body)
    before = (corpus.directory / "review.json").read_bytes()
    entity, observation = document["entries"]
    with pytest.raises(ValidationError):
        review.set_decision(corpus.directory,
            observation["record_id"] if failure == "approve_held" else entity["record_id"],
            "excluded" if failure == "exclude_without_reason" else "approved",
            reviewer=None if failure == "approve_without_reviewer" else "test")
    assert (corpus.directory / "review.json").read_bytes() == before


@pytest.mark.parametrize("field", ["record", "quarantine_reasons", "point_id", "duplicate_id", "missing_id", "fingerprint"])
def test_review_tampering_rejected(corpus, field):
    document = extract_one(corpus)
    if field == "record":
        document["entries"][0]["record"]["name"] = "Invented entity"
    elif field == "quarantine_reasons":
        document["entries"][0]["quarantine_reasons"] = ["fabricated"]
    elif field == "point_id":
        document["entries"][0]["point_id"] = BUILD
    elif field == "duplicate_id":
        document["entries"][1] = document["entries"][0]
    elif field == "missing_id":
        document["entries"].pop()
    else:
        document["candidate_fingerprint"] = "fake"
    (corpus.directory / "review.json").write_text(json.dumps(document))
    with pytest.raises(ValueError):
        review.validate(corpus.directory, export=True)
    assert not (corpus.directory / "reviewed.json").exists()


def test_changed_candidates_require_new_review_file_without_overwriting_old_decisions(corpus):
    extract_one(corpus)
    previous = (corpus.directory / "review.json").read_bytes()
    component, _, client = sdk_component(corpus.settings, [records("M22 has distance 4.27 ± 0.14 kpc.")])
    try:
        jobs.extract(corpus.directory, corpus.settings, max_calls=1, component=component)
    finally:
        client.close()
    with pytest.raises(ValueError, match="stale"):
        review.prepare(corpus.directory)
    assert (corpus.directory / "review.json").read_bytes() == previous
    result = review.prepare(corpus.directory, filename="review-batch2.json")
    assert result["decisions"] == {"needs_review": 4}


@pytest.mark.parametrize("filename", [".env", "plan.json", "candidates.json", "failures.json", "reviewed.json", "../outside.json"])
def test_protected_review_paths(corpus, filename):
    extract_one(corpus)
    with pytest.raises(ValueError, match="sidecar"):
        review.prepare(corpus.directory, filename=filename)


def test_review_commands_do_not_load_settings(corpus, monkeypatch, capsys):
    extract_one(corpus)
    from pathlib import Path
    original = Path.read_text
    def checked(path, *args, **kwargs):
        assert path.name != ".env"
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", checked)
    capsys.readouterr()
    main(["review-prepare", "--output", str(corpus.directory)])
    assert json.loads(capsys.readouterr().out)["model_calls"] == 0
    main(["review-export", "--output", str(corpus.directory)])
    assert json.loads(capsys.readouterr().out)["graph_ready"] is False
