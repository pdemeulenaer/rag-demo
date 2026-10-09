"""Rebase a reviewed dataset onto current builds without regenerating questions.

The source dataset and snapshot remain immutable.  Approval is retained only when
the complete ordered text evidence for every paper used by a question is identical
between the old and current build.  Changed or incompletely mapped questions are
downgraded to needs_review.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
from qdrant_client import QdrantClient

from evals.generate_questions import EvaluationSettings, active_builds
from evals.review_dataset import (
    ReviewDatasetError,
    ReviewedDatasetV2,
    canonical_hash,
    load_files,
    validate_v2,
    write_json,
)
from src.api.papers.catalogue import Catalogue, snapshot_id
from src.api.papers.consistency import expected_ids
from src.api.papers.settings import PaperSettings
from src.api.rag.sparse import SPARSE_VECTOR_NAME


class RebaseError(ValueError):
    """Operator-facing error that does not include service credentials."""


def _page(payload: dict) -> str | None:
    value = payload.get("page_number", payload.get("page"))
    return None if value is None else str(value)


def _signature(payload: dict) -> tuple[str, str | None, str, str]:
    return (
        str(payload.get("text") or ""),
        _page(payload),
        str(payload.get("section_header") or ""),
        str(payload.get("content_kind") or "text"),
    )


def _text_points(client, build: dict) -> dict[str, dict]:
    ids = expected_ids(build)
    if not ids or len(ids) != len(set(ids)):
        raise RebaseError(f"Build {build['id']} has no valid point manifest; run papers-audit")
    found: dict[str, dict] = {}
    seen: set[str] = set()
    for start in range(0, len(ids), 128):
        batch = ids[start:start + 128]
        points = client.retrieve(
            collection_name=build["collection"],
            ids=[int(value) if value.isdecimal() else value for value in batch],
            with_payload=True,
            with_vectors=False,
        )
        for point in points:
            seen.add(str(point.id))
            payload = point.payload or {}
            legacy = (build.get("manifest") or {}).get("legacy_filter")
            if (not legacy and (str(payload.get("build_id")) != str(build["id"])
                    or str(payload.get("paper_id")) != str(build["paper_id"]))):
                raise RebaseError(
                    f"Build {build['id']} has point identity drift; run papers-audit"
                )
            if payload.get("type", "text") in {"text", "chunk"}:
                found[str(point.id)] = payload
    missing = set(ids).difference(seen)
    if missing:
        raise RebaseError(f"Build {build['id']} is missing indexed points; run papers-audit")
    return found


def _ordered(points: dict[str, dict]) -> list[tuple[int | None, tuple[str, str | None, str, str]]]:
    rows = []
    for point_id, payload in points.items():
        index = payload.get("chunk_index")
        if isinstance(index, bool) or not isinstance(index, int):
            index = None
        rows.append((index, _signature(payload), point_id))
    rows.sort(key=lambda row: (row[0] is None, row[0] if row[0] is not None else 0,
                               row[1], row[2]))
    return [(index, signature) for index, signature, _ in rows]


def _stable_order(points: dict[str, dict]) -> bool:
    indexes = [payload.get("chunk_index") for payload in points.values()]
    return (
        all(isinstance(value, int) and not isinstance(value, bool) for value in indexes)
        and sorted(indexes) == list(range(len(indexes)))
    )


def _point_mapping(old_points: dict[str, dict], new_points: dict[str, dict]) -> dict[str, str]:
    """Map only unambiguous, exact text/page/section/content matches."""
    by_index = {
        payload.get("chunk_index"): (point_id, payload)
        for point_id, payload in new_points.items()
        if isinstance(payload.get("chunk_index"), int)
        and not isinstance(payload.get("chunk_index"), bool)
    }
    by_signature: dict[tuple, list[str]] = {}
    for point_id, payload in new_points.items():
        by_signature.setdefault(_signature(payload), []).append(point_id)
    result = {}
    for old_id, old_payload in old_points.items():
        index = old_payload.get("chunk_index")
        indexed = by_index.get(index) if isinstance(index, int) and not isinstance(index, bool) else None
        if indexed and _signature(indexed[1]) == _signature(old_payload):
            result[old_id] = indexed[0]
            continue
        candidates = by_signature.get(_signature(old_payload), [])
        if len(candidates) == 1:
            result[old_id] = candidates[0]
    return result


def _paper_ids(question: dict, old_evidence: dict[str, dict]) -> set[str]:
    result = {str(value) for value in question.get("paper_ids", []) if value}
    result.update(str(row["paper_id"]) for row in question.get("reference_evidence", [])
                  if isinstance(row, dict) and row.get("paper_id"))
    for evidence_id in question.get("generation_evidence_ids", []):
        row = old_evidence.get(str(evidence_id))
        if row and row.get("paper_id"):
            result.add(str(row["paper_id"]))
    return result


def _metadata_signature(paper: dict, metadata: dict | None = None) -> tuple:
    values = paper if metadata is None else metadata
    published = values.get("published") or values.get("year")
    return (
        str(values.get("title") or values.get("file_name") or ""),
        str(values.get("abstract") or ""),
        tuple(str(value) for value in values.get("authors", [])),
        str(published)[:4] if published else None,
        tuple(sorted(str(value) for value in values.get("categories", []))),
    )


def _rebased_evidence(old: dict, new_build: dict, point_id: str,
                      payload: dict) -> dict:
    metadata = new_build.get("metadata") or {}
    result = dict(old)
    result.update(
        point_id=point_id,
        collection=new_build["collection"],
        paper_id=new_build["paper_id"],
        build_id=new_build["id"],
        version=new_build["version"],
        title=metadata.get("title") or metadata.get("file_name") or old.get("title"),
        page_number=payload.get("page_number", payload.get("page")),
        source_url=payload.get("source_url") or old.get("source_url"),
        text=str(payload.get("text") or "")[:2400],
        section_header=payload.get("section_header") or "",
        content_kind=payload.get("content_kind") or "text",
    )
    return result


def rebase(reviewed: dict, old_snapshot: dict, *, catalogue, client,
           settings, options, source_dataset: Path) -> tuple[dict, dict, dict]:
    if reviewed.get("schema_version") != 2:
        raise RebaseError("Only reviewed schema-v2 datasets can be rebased safely")
    try:
        ReviewedDatasetV2.model_validate(reviewed)
        validate_v2(
            reviewed,
            old_snapshot,
            require_splits=reviewed.get("split_policy") is not None,
        )
    except Exception as error:
        raise RebaseError("Source reviewed dataset is not a valid schema-v2 review") from error

    old_papers = old_snapshot.get("papers") or []
    if not old_papers:
        raise RebaseError("Source snapshot contains no papers")
    old_paper_ids = {str(row.get("paper_id")) for row in old_papers if row.get("paper_id")}
    if len(old_paper_ids) != len(old_papers):
        raise RebaseError("Source snapshot has missing or duplicate paper identities")
    collections = {row.get("collection") for row in old_papers}
    if len(collections) != 1 or None in collections:
        raise RebaseError("Rebase requires a source snapshot with exactly one collection")

    current = active_builds(catalogue, settings, options, old_snapshot.get("source", "arxiv"))
    current_by_paper = {str(build["paper_id"]): build for build in current}
    missing_papers = sorted(old_paper_ids.difference(current_by_paper))
    if missing_papers:
        raise RebaseError(
            f"{len(missing_papers)} source papers have no current active build; finish re-indexing"
        )
    selected = [current_by_paper[str(row["paper_id"])] for row in old_papers]
    target_collections = {row["collection"] for row in selected}
    if len(target_collections) != 1:
        raise RebaseError("Current builds span multiple collections; use one corpus per dataset")
    for build in selected:
        index = (build.get("manifest") or {}).get("retrieval_index") or {}
        if index.get("sparse_vector_name") != SPARSE_VECTOR_NAME:
            raise RebaseError("Current corpus is not fully re-indexed with BM25 sparse vectors")

    evidence_rows = [row for row in old_snapshot.get("evidence", [])
                     if isinstance(row, dict) and row.get("evidence_id")]
    known_evidence_ids = {str(row["evidence_id"]) for row in evidence_rows}
    for question in reviewed["questions"]:
        for row in question.get("reference_evidence", []):
            if (isinstance(row, dict) and row.get("evidence_id")
                    and str(row["evidence_id"]) not in known_evidence_ids):
                evidence_rows.append(row)
                known_evidence_ids.add(str(row["evidence_id"]))
    old_evidence = {str(row["evidence_id"]): row for row in evidence_rows}
    mapped_evidence: dict[str, dict] = {}
    paper_equivalent: dict[str, bool] = {}
    paper_reports = []

    for old_paper, new_build in zip(old_papers, selected):
        paper_id = str(old_paper["paper_id"])
        old_build = catalogue.get_build(str(old_paper["build_id"]))
        if not old_build or old_build.get("paper_id") != paper_id:
            raise RebaseError(f"Historical build for paper {paper_id} is unavailable in PostgreSQL")
        if old_build.get("collection") != old_paper.get("collection"):
            raise RebaseError(f"Historical collection identity drift for paper {paper_id}")
        old_points = _text_points(client, old_build)
        new_points = _text_points(client, new_build)
        point_map = _point_mapping(old_points, new_points)
        same_version = old_build.get("version") == new_build.get("version")
        same_text = (
            _stable_order(old_points)
            and _stable_order(new_points)
            and _ordered(old_points) == _ordered(new_points)
        )
        same_metadata = _metadata_signature(old_paper) == _metadata_signature(
            old_paper, new_build.get("metadata") or {}
        )
        equivalent = same_version and same_text and same_metadata
        paper_equivalent[paper_id] = equivalent
        old_ids_for_paper = {
            str(row["evidence_id"]): row for row in evidence_rows
            if isinstance(row, dict) and str(row.get("paper_id")) == paper_id
        }
        mapped = 0
        for evidence_id, old_row in old_ids_for_paper.items():
            new_point_id = point_map.get(str(old_row.get("point_id")))
            if not new_point_id:
                continue
            mapped_evidence[evidence_id] = _rebased_evidence(
                old_row, new_build, new_point_id, new_points[new_point_id]
            )
            mapped += 1
        paper_reports.append({
            "paper_id": paper_id,
            "old_build_id": old_build["id"],
            "new_build_id": new_build["id"],
            "old_collection": old_build["collection"],
            "new_collection": new_build["collection"],
            "same_version": same_version,
            "identical_text_stream": same_text,
            "identical_scientific_metadata": same_metadata,
            "approval_equivalent": equivalent,
            "sampled_evidence": len(old_ids_for_paper),
            "mapped_sampled_evidence": mapped,
        })

    new_papers = []
    for old_paper, build in zip(old_papers, selected):
        metadata = build.get("metadata") or {}
        evidence_ids = [value for value in old_paper.get("evidence_ids", [])
                        if value in mapped_evidence]
        published = metadata.get("published") or metadata.get("year")
        new_papers.append({
            **old_paper,
            "build_id": build["id"],
            "collection": build["collection"],
            "version": build["version"],
            "embedding_model": build["embedding_model"],
            "title": metadata.get("title") or metadata.get("file_name") or old_paper.get("title"),
            "abstract": metadata.get("abstract", old_paper.get("abstract", "")),
            "authors": metadata.get("authors", old_paper.get("authors", [])),
            "year": str(published)[:4] if published else old_paper.get("year"),
            "categories": metadata.get("categories", old_paper.get("categories", [])),
            "evidence_ids": evidence_ids,
        })

    snapshot = {
        **old_snapshot,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope_id": settings.scope_id,
        "corpus_fingerprint": snapshot_id(selected),
        "active_build_ids": [build["id"] for build in selected],
        "excluded_no_text_build_ids": [],
        "papers": new_papers,
        "evidence": [mapped_evidence[row["evidence_id"]]
                     for row in evidence_rows
                     if row.get("evidence_id") in mapped_evidence],
        "rebased_from": {
            "snapshot_hash": canonical_hash(old_snapshot),
            "dataset": str(source_dataset),
            "policy": "exact-text-stream-v1",
        },
    }

    questions = []
    retained = downgraded = 0
    for original in reviewed["questions"]:
        question = deepcopy(original)
        papers = _paper_ids(question, old_evidence)
        reference_ids = [str(row.get("evidence_id")) for row in
                         question.get("reference_evidence", []) if row.get("evidence_id")]
        safe = (
            bool(papers)
            and all(paper_equivalent.get(paper, False) for paper in papers)
            and all(evidence_id in mapped_evidence for evidence_id in reference_ids)
        )
        if (question.get("kind") == "unanswerable_candidate"
                and question.get("answerability_scope") == "frozen_corpus"):
            safe = safe and all(paper_equivalent.values())
        question["reference_evidence"] = [mapped_evidence[evidence_id]
                                          for evidence_id in reference_ids
                                          if evidence_id in mapped_evidence]
        question["generation_evidence_ids"] = [
            evidence_id for evidence_id in question.get("generation_evidence_ids", [])
            if evidence_id in mapped_evidence
        ]
        mapped_question_evidence_ids = {
            *(
                str(row.get("evidence_id"))
                for row in question["reference_evidence"]
                if row.get("evidence_id")
            ),
            *question["generation_evidence_ids"],
        }
        mapped_papers = {
            str(mapped_evidence[evidence_id]["paper_id"])
            for evidence_id in mapped_question_evidence_ids
            if evidence_id in mapped_evidence
            and mapped_evidence[evidence_id].get("paper_id")
        }
        # A partially mapped pending question must describe only the papers
        # represented by its retained evidence. If no evidence mapped at all,
        # retain the original paper identity so a reviewer knows where to repair it.
        question["paper_ids"] = sorted(mapped_papers or papers)
        question["group_id"] = None
        question["split"] = None
        question["rebase_status"] = "exact" if safe else "needs_review"
        missing_references = sorted(set(reference_ids).difference(mapped_evidence))
        if missing_references:
            question["rebase_unmatched_evidence_ids"] = missing_references
        if question.get("review_status") == "approved":
            if safe:
                retained += 1
            else:
                downgraded += 1
                if question.get("review") is not None:
                    question["previous_review"] = question["review"]
                question["review_status"] = "needs_review"
                question["review"] = None
        questions.append(question)

    plan = {
        "schema_version": 1,
        "operation": "evaluation-dataset-rebase",
        "policy": "exact-text-stream-v1",
        "source_dataset": str(source_dataset),
        "source_snapshot_hash": canonical_hash(old_snapshot),
        "target_snapshot_hash": canonical_hash(snapshot),
    }
    output = {
        "schema_version": 2,
        "snapshot_hash": canonical_hash(snapshot),
        "plan_hash": canonical_hash(plan),
        "split_policy": None,
        "questions": questions,
    }
    # Validate the structural contract even when every approval needs renewed review.
    try:
        ReviewedDatasetV2.model_validate(output)
    except Exception as error:
        raise RebaseError("Rebased dataset failed schema validation") from error
    report = {
        **plan,
        "plan_hash": output["plan_hash"],
        "papers": len(selected),
        "identical_papers": sum(paper_equivalent.values()),
        "mapped_sampled_evidence": len(mapped_evidence),
        "source_sampled_evidence": len(old_evidence),
        "approved_retained": retained,
        "approved_downgraded": downgraded,
        "paper_results": paper_reports,
    }
    return snapshot, output, report


def run(dataset: Path, output: Path, *, catalogue=None, client=None,
        settings=None, options=None) -> dict:
    if not dataset.is_file():
        raise RebaseError(f"Source reviewed dataset is missing: {dataset}")
    if output.exists():
        raise RebaseError(f"Output directory already exists: {output}")
    reviewed, old_snapshot = load_files(dataset)
    settings = settings or PaperSettings()
    options = options or EvaluationSettings()
    own_catalogue = catalogue is None
    own_client = client is None
    if own_catalogue:
        catalogue = Catalogue(settings.PAPERS_DATABASE_URL)
    try:
        catalogue.require_schema()
        if own_client:
            port = options.QDRANT_PORT if options.QDRANT_PORT is not None else (
                443 if options.QDRANT_URL.startswith("https://") else 6333
            )
            client = QdrantClient(
                url=options.QDRANT_URL,
                port=port,
                api_key=options.QDRANT_API_KEY or None,
            )
        snapshot, rebased, report = rebase(
            reviewed,
            old_snapshot,
            catalogue=catalogue,
            client=client,
            settings=settings,
            options=options,
            source_dataset=dataset,
        )
        output.mkdir(parents=True, mode=0o700, exist_ok=False)
        write_json(output / "snapshot.json", snapshot)
        write_json(output / "questions.reviewed.json", rebased)
        write_json(output / "rebase.json", report)
        result = {
            "output": str(output),
            "papers": report["papers"],
            "identical_papers": report["identical_papers"],
            "approved_retained": report["approved_retained"],
            "approved_downgraded": report["approved_downgraded"],
        }
        print(json.dumps(result, indent=2))
        return result
    finally:
        if own_client and client is not None:
            client.close()
        if own_catalogue:
            catalogue.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        run(args.dataset, args.output)
    except (RebaseError, ReviewDatasetError) as error:
        print(f"Evaluation rebase failed: {error}")
        raise SystemExit(1) from None
    except Exception as error:
        print(f"Evaluation rebase failed ({type(error).__name__}); check catalogue and Qdrant health")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
