"""Assemble hand-curated KG development questions from validated local source records.

No question generation, service access or automatic semantic approval. The specification
contains the curator's answers/decisions; assembly only checks provenance and format.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from evals.review_dataset import (
    ReviewedQuestionV2, _expected_components, canonical_hash, component_id,
    validate_v2, write_json,
)


def assemble(spec: dict, snapshot: dict, plan: dict, review: dict,
             dependency_held: list[str]) -> dict:
    """Pure assembly; caller first validates the KG checkpoints/review sidecar."""
    if (spec["snapshot_hash"] != canonical_hash(snapshot)
            or spec["kg_plan_id"] != plan["plan_id"]
            or spec["kg_plan_id"] != review["plan_id"]
            or spec["candidate_fingerprint"] != review["candidate_fingerprint"]):
        raise ValueError("Curated specification does not match frozen KG/snapshot inputs")
    plan_body = {key: value for key, value in plan.items() if key != "plan_id"}
    digest = sha256(json.dumps(plan_body, ensure_ascii=False, sort_keys=True,
                              separators=(",", ":")).encode()).hexdigest()
    if digest != plan["plan_id"]:
        raise ValueError("KG plan hash mismatch")
    chunks = {c["point_id"]: c for c in plan["chunks"]}
    kg_papers = {p["build_id"]: p for p in plan["papers"]}
    papers = {p["build_id"]: p for p in snapshot["papers"]}
    approved = {(entry["point_id"], entry["record_id"].rsplit(":", 1)[-1]): entry
                for entry in review["entries"] if entry["decision"] == "approved"
                and not entry["quarantine_reasons"]
                and entry["record_id"] not in dependency_held}
    questions = []
    for curated in spec["questions"]:
        references, records = {}, []
        for selection in curated["sources"]:
            point = selection["point_id"]
            chunk = chunks[point]
            paper = papers.get(chunk["build_id"])
            kg_paper = kg_papers[chunk["build_id"]]
            if (not paper or chunk["build_id"] not in snapshot["active_build_ids"]
                    or any(paper[key] != chunk[key] for key in ("paper_id", "collection", "source"))
                    or paper["version"] != kg_paper["version"]):
                raise ValueError("KG source is outside the frozen evaluation scope")
            if not selection["record_ids"]:
                raise ValueError("Every source must select an eligible approved record")
            for local_id in selection["record_ids"]:
                entry = approved.get((point, local_id))
                if entry is None:
                    raise ValueError(f"Source record is not approved/eligible: {point}:{local_id}")
                record = entry["record"]
                for evidence in record["evidence"]:
                    if (any(evidence[key] != chunk[key] for key in
                            ("paper_id", "build_id", "collection", "source", "point_id", "page_number"))
                            or not evidence["quote"] or evidence["quote"] not in chunk["text"]):
                        raise ValueError("Reviewed quote or identity differs from original chunk")
                records.append({"record_id": entry["record_id"], "point_id": point,
                                "record_type": entry["record_type"],
                                "source_quotes": [e["quote"] for e in record["evidence"]]})
            source_id = kg_paper.get("source_id")
            source_url = (f"https://arxiv.org/abs/{source_id}v{paper['version']}"
                          if source_id and paper["source"] == "arxiv" else None)
            references[point] = {
                **chunk, "evidence_id": canonical_hash(chunk)[:24],
                "version": paper["version"], "title": paper["title"],
                "source_url": source_url,
                "content_kind": "text",
            }
        questions.append({
            **{k: curated[k] for k in ("id", "kind", "profile", "question", "reference_answer")},
            "required_numeric_values": curated.get("required_numeric_values", []),
            "review_status": "approved", "answerability_scope": "supplied_excerpts_only",
            "reference_evidence": list(references.values()), "generation_evidence_ids": [],
            "paper_ids": sorted({r["paper_id"] for r in references.values()}),
            "review": {**spec["review"], "notes": curated["review_notes"]},
            "kg_reference": {"publication_id": spec["publication_id"],
                             "plan_id": plan["plan_id"], "records": records},
        })
    dataset = {"schema_version": 2, "snapshot_hash": canonical_hash(snapshot),
               "plan_hash": canonical_hash(spec), "questions": questions}
    _, normalized = validate_v2(dataset, snapshot, require_splits=False)
    components = _expected_components([ReviewedQuestionV2.model_validate(q) for q in normalized])
    for question in questions:
        question["split"] = "development"
        question["group_id"] = component_id(components[question["paper_ids"][0]])
    # All items are deliberately development-only, not a newly claimed held-out test.
    dataset["split_policy"] = {"name": "development-only-v1", "seed": 42,
                               "requested_test_ratio": None, "actual_test_ratio": 0.0,
                               "development_questions": len(questions), "test_questions": 0}
    validate_v2(dataset, snapshot, selected_split="development")
    return dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--kg-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # This existing validator checks authoritative checkpoints, not reviewed.json.
    # Its optional KG dependency imports neither API Config nor .env.
    from src.api.kg.review import validate
    report = validate(args.kg_dir)
    read = lambda path: json.loads(path.read_text(encoding="utf-8"))
    spec, snapshot = read(args.spec), read(args.snapshot)
    dataset = assemble(spec, snapshot, read(args.kg_dir / "plan.json"),
                       read(args.kg_dir / "review.json"), report["approved_but_dependency_held"])
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "snapshot.json", snapshot)
    write_json(args.output / "curation.json", spec)
    write_json(args.output / "questions.reviewed.json", dataset)
    print(json.dumps({"output": str(args.output), "questions": len(dataset["questions"]),
                      "split": "development", "model_calls": 0, "database_writes": 0,
                      "publication_id": spec["publication_id"]}, indent=2))


if __name__ == "__main__":
    main()
