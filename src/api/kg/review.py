"""Local, attributed scientific review; never edit raw extraction or publish graphs."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .contracts import Record, Text
from .jobs import canonical, directory_lock, validated_snapshot


class ReviewEntry(Record):
    record_id: Text
    point_id: Text
    record_type: Literal["entity", "observation", "relationship"]
    record: dict
    quarantine_reasons: list[str]
    decision: Literal["needs_review", "approved", "excluded"] = "needs_review"
    reason: Literal["presentation_only", "unsupported", "incorrect_type", "duplicate", "other"] | None = None
    reviewer: Text | None = None
    notes: str = ""

    @model_validator(mode="after")
    def attributable_decision(self):
        if self.decision != "needs_review" and not self.reviewer:
            raise ValueError("Review decisions need a reviewer")
        if self.decision == "excluded" and self.reason is None:
            raise ValueError("Exclusions need an explicit reason")
        if self.decision == "approved" and (self.reason is not None or self.quarantine_reasons):
            raise ValueError("Quarantined records cannot be approved; approval has no exclusion reason")
        return self


class ReviewDocument(Record):
    schema_version: Literal["kg-review-v1"] = "kg-review-v1"
    plan_id: Text
    candidate_fingerprint: Text
    entries: list[ReviewEntry] = Field(default_factory=list)


def _path(directory, name):
    # Sidecars only: never use .env, extraction inputs or checkpoints as outputs.
    if (Path(name).name != name or not name.endswith(".json") or name in
            {"plan.json", "candidates.json", "failures.json", "reviewed.json"}):
        raise ValueError("Review filename must be a separate local JSON sidecar")
    path = directory / name
    if path.is_symlink():
        raise ValueError("Review sidecar must not be a symlink")
    return path


def _snapshot(directory):
    validation, plan, chunks = validated_snapshot(directory)
    entries = []
    for point_id, saved in chunks:
        quarantine = {r["record_id"]: r["reasons"] for r in saved.quarantine}
        for kind, group in (("entity", saved.batch.entities), ("observation", saved.batch.observations),
                            ("relationship", saved.batch.relationships)):
            for record in group:
                entries.append(ReviewEntry(record_id=record.id, point_id=point_id, record_type=kind,
                    record=record.model_dump(mode="json"), quarantine_reasons=quarantine.get(record.id, [])))
    ids = [entry.record_id for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("Review records must have globally unique scoped identities")
    if not entries:
        raise ValueError("No completed scientific records are available for review")
    fingerprint = sha256(canonical(dict(plan_id=plan["plan_id"],
        chunks=[dict(point_id=p, result=s.model_dump(mode="json")) for p, s in chunks])).encode()).hexdigest()
    return ReviewDocument(plan_id=plan["plan_id"], candidate_fingerprint=fingerprint, entries=entries), validation, chunks


def _load(path, expected):
    document = ReviewDocument.model_validate_json(path.read_text(encoding="utf-8"))
    if document.plan_id != expected.plan_id or document.candidate_fingerprint != expected.candidate_fingerprint:
        raise ValueError("Review is stale; prepare a new review filename for changed candidates")
    trusted = {entry.record_id: entry for entry in expected.entries}
    if (len(document.entries) != len(trusted) or {entry.record_id for entry in document.entries} != set(trusted)):
        raise ValueError("Review IDs are duplicated, missing or out of scope")
    for entry in document.entries:
        source = trusted[entry.record_id]
        if any(getattr(entry, field) != getattr(source, field) for field in
               ("point_id", "record_type", "record", "quarantine_reasons")):
            raise ValueError("Review source records or quarantine metadata were changed")
    return document


def _write(path, data):
    temporary = path.with_suffix(".tmp")
    if temporary.is_symlink():
        raise ValueError("Review temporary file must not be a symlink")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _summary(document, validation, chunks):
    from .extraction import staging_graph
    approved = {entry.record_id for entry in document.entries if entry.decision == "approved"}
    graphs = [dict(point_id=point, graph=staging_graph(saved.batch, approved_ids=approved).model_dump(mode="json"))
              for point, saved in chunks]
    # Implicit HAS_OBSERVATION links are not reviewed assertion IDs.
    eligible = {n["id"] for chunk in graphs for n in chunk["graph"]["nodes"]}
    for chunk in graphs:
        for edge in chunk["graph"]["relationships"]:
            if "record_json" in (edge.get("properties") or {}):
                eligible.add(json.loads(edge["properties"]["record_json"])["id"])
    decisions = Counter(entry.decision for entry in document.entries)
    return dict(valid=True, plan_id=document.plan_id, candidate_fingerprint=document.candidate_fingerprint,
        decisions=dict(decisions), quarantined_records=sum(bool(e.quarantine_reasons) for e in document.entries),
        eligible_records=len(eligible), approved_but_dependency_held=sorted(approved-eligible),
        review_complete=all(e.decision != "needs_review" for e in document.entries),
        extraction_complete=validation["complete"], graph_ready=False, model_calls=0), graphs


def prepare(directory, *, filename="review.json"):
    with directory_lock(directory):
        path = _path(directory, filename)
        expected, validation, chunks = _snapshot(directory)
        if path.exists():
            document = _load(path, expected)  # Preserve decisions, including user formatting.
        else:
            document = expected
            _write(path, document.model_dump(mode="json"))
        return _summary(document, validation, chunks)[0] | dict(review=str(path))


def set_decision(directory, record_id, decision, *, reviewer, reason=None, notes="", filename="review.json"):
    with directory_lock(directory):
        path = _path(directory, filename)
        expected, validation, chunks = _snapshot(directory)
        document = _load(path, expected)
        found = False
        for index, entry in enumerate(document.entries):
            if entry.record_id == record_id:
                document.entries[index] = ReviewEntry.model_validate(entry.model_dump() | dict(
                    decision=decision, reviewer=reviewer, reason=reason, notes=notes))
                found = True
        if not found:
            raise ValueError("Review record ID is not in this frozen candidate set")
        _write(path, document.model_dump(mode="json"))
        return _summary(document, validation, chunks)[0] | dict(review=str(path))


def validate(directory, *, filename="review.json", export=False):
    with directory_lock(directory):
        expected, validation, chunks = _snapshot(directory)
        path = _path(directory, filename)
        document = _load(path, expected)
        report, graphs = _summary(document, validation, chunks)
        if export:
            destination = directory / "reviewed.json"
            if destination.is_symlink():
                raise ValueError("Reviewed output must not be a symlink")
            _write(destination, report | dict(chunks=graphs,
                decisions=[e.model_dump(mode="json") for e in document.entries]))
            report["output"] = str(destination)
        return report | dict(review=str(path))
