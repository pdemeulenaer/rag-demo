"""Offline source-curation assembly; no services, model calls or local .env."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from evals.curate_kg_dataset import assemble
from evals.review_dataset import canonical_hash, validate_v2


def inputs():
    paper = {"paper_id": "paper-1", "build_id": "build-1", "collection": "papers",
             "source": "arxiv", "version": 2, "title": "A synthetic study",
             "source_id": "2601.00001"}
    chunk = {k: paper[k] for k in ("paper_id", "build_id", "collection", "source")}
    chunk |= {"point_id": "point-1", "page_number": 3, "section_header": "Results",
              "text": "The measured value is 7 units. No stronger result is claimed."}
    record = {"id": "build-1:revision:point-1:o1", "statement": "Value is 7 units.",
              "evidence": [{**{k: v for k, v in chunk.items() if k != "text"},
                            "quote": "The measured value is 7 units."}]}
    plan = {"chunks": [chunk], "papers": [paper]}
    rehash_plan(plan)
    snapshot = {"papers": [paper], "active_build_ids": ["build-1"], "evidence": []}
    review = {"plan_id": plan["plan_id"], "candidate_fingerprint": "fingerprint",
              "entries": [{"record_id": record["id"], "point_id": "point-1",
                           "record_type": "observation", "record": record,
                           "decision": "approved", "quarantine_reasons": []}]}
    spec = {"snapshot_hash": canonical_hash(snapshot), "kg_plan_id": plan["plan_id"],
            "candidate_fingerprint": "fingerprint", "publication_id": "publication:fixture",
            "review": {"reviewer": "AI source curator (not specialist validation)",
                       "reviewed_at": "2026-10-20T08:29:44Z", "decision": "approved",
                       "original_sources_checked": True},
            "questions": [{"id": "kg1", "kind": "single_paper", "profile": "single_fact",
                           "question": "What value was measured?", "reference_answer": "7 units.",
                           "review_notes": "Checked original synthetic source.",
                           "sources": [{"point_id": "point-1", "record_ids": ["o1"]}]}]}
    return spec, snapshot, plan, review


def rehash_plan(plan):
    content = {k: v for k, v in plan.items() if k != "plan_id"}
    plan["plan_id"] = sha256(json.dumps(content, ensure_ascii=False, sort_keys=True,
                                       separators=(",", ":")).encode()).hexdigest()


def test_curated_sources_keep_full_text_scope_and_attribution_without_mutation():
    args = inputs()
    before = deepcopy(args)
    data = assemble(*args, [])
    assert args == before
    _, rows = validate_v2(data, args[1], selected_split="development")
    assert len(rows) == 1
    question = rows[0]
    assert question["reference_evidence"][0]["text"] == args[2]["chunks"][0]["text"]
    assert question["reference_evidence"][0]["source_url"] == "https://arxiv.org/abs/2601.00001v2"
    assert question["review"]["reviewer"].startswith("AI source curator")
    assert question["kg_reference"]["records"][0]["record_id"].endswith(":o1")
    assert data["snapshot_hash"] == canonical_hash(args[1])
    assert data["split_policy"]["test_questions"] == 0
    assert data["split_policy"]["name"] == "development-only-v1"
    assert data["split_policy"]["requested_test_ratio"] is None
    assert assemble(*args, []) == data


@pytest.mark.parametrize("change", ["snapshot", "fingerprint", "plan_id"])
def test_stale_curated_input_is_rejected(change):
    spec, snapshot, plan, review = inputs()
    if change == "snapshot":
        snapshot["active_build_ids"].append("other-build")
    elif change == "fingerprint":
        review["candidate_fingerprint"] = "changed"
    else:
        spec["kg_plan_id"] = "changed"
    with pytest.raises(ValueError, match="does not match"):
        assemble(spec, snapshot, plan, review, [])


def test_tampered_plan_text_is_rejected():
    spec, snapshot, plan, review = inputs()
    plan["chunks"][0]["text"] = "A changed number is 9."
    with pytest.raises(ValueError, match="plan hash"):
        assemble(spec, snapshot, plan, review, [])


@pytest.mark.parametrize("status", ["needs_review", "excluded", "quarantined", "dependency_held"])
def test_only_eligible_approved_records_may_supply_references(status):
    spec, snapshot, plan, review = inputs()
    held = []
    entry = review["entries"][0]
    if status == "quarantined":
        entry["quarantine_reasons"] = ["damaged_value"]
    elif status == "dependency_held":
        held = [entry["record_id"]]
    else:
        entry["decision"] = status
    with pytest.raises(ValueError, match="not approved/eligible"):
        assemble(spec, snapshot, plan, review, held)


@pytest.mark.parametrize("change", ["quote", "paper_id", "point_id", "page_number"])
def test_quote_and_source_identity_cannot_be_invented(change):
    spec, snapshot, plan, review = inputs()
    review["entries"][0]["record"]["evidence"][0][change] = "invented"
    with pytest.raises(ValueError, match="quote or identity"):
        assemble(spec, snapshot, plan, review, [])


@pytest.mark.parametrize("change", ["version", "active_scope"])
def test_out_of_snapshot_build_or_version_cannot_supply_evidence(change):
    spec, snapshot, plan, review = inputs()
    if change == "version":
        snapshot["papers"][0] = {**snapshot["papers"][0], "version": 3}
    else:
        snapshot["active_build_ids"] = []
    spec["snapshot_hash"] = canonical_hash(snapshot)
    with pytest.raises(ValueError, match="outside the frozen"):
        assemble(spec, snapshot, plan, review, [])


@pytest.mark.parametrize("field,value", [("requested_test_ratio", 0.25),
                                       ("actual_test_ratio", 0.25), ("test_questions", 1)])
def test_development_only_cannot_claim_a_test_allocation(field, value):
    args = inputs()
    dataset = assemble(*args, [])
    dataset["split_policy"][field] = value
    with pytest.raises(ValueError, match="Development-only"):
        validate_v2(dataset, args[1])


def test_existing_paper_split_policy_still_requires_a_test_ratio():
    args = inputs()
    dataset = assemble(*args, [])
    dataset["split_policy"]["name"] = "paper-components-v1"
    with pytest.raises(ValueError, match="require a requested test ratio"):
        validate_v2(dataset, args[1])
