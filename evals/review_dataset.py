"""Validate and split human-reviewed evaluation datasets without service calls."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import random
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


QuestionKind = Literal["single_paper", "cross_paper", "unanswerable_candidate"]
ReviewStatus = Literal["needs_review", "approved", "rejected"]
DatasetSplit = Literal["development", "test"]


class ReviewDatasetError(ValueError):
    """Operator-facing reviewed-dataset validation error."""


class ReviewMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reviewer: str = Field(min_length=1)
    reviewed_at: datetime
    decision: Literal["approved", "rejected"]
    original_sources_checked: bool
    corpus_search_verified: bool = False
    notes: str | None = None


class ReviewedQuestionV2(BaseModel):
    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    id: str = Field(min_length=1)
    kind: QuestionKind
    question: str = Field(min_length=1)
    reference_answer: str = Field(min_length=1)
    review_status: ReviewStatus
    answerability_scope: Literal["supplied_excerpts_only", "frozen_corpus"]
    reference_evidence: list[dict]
    generation_evidence_ids: list[str] = Field(default_factory=list)
    paper_ids: list[str] = Field(default_factory=list)
    group_id: str | None = None
    split: DatasetSplit | None = None
    review: ReviewMetadata | None = None


class SplitPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Literal["paper-components-v1"]
    seed: int
    requested_test_ratio: float = Field(gt=0, lt=1)
    actual_test_ratio: float = Field(ge=0, le=1)
    development_questions: int = Field(ge=0)
    test_questions: int = Field(ge=0)


class ReviewedDatasetV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[2]
    snapshot_hash: str = Field(min_length=1)
    plan_hash: str = Field(min_length=1)
    split_policy: SplitPolicy | None = None
    questions: list[ReviewedQuestionV2]


def canonical_hash(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _read_json(path: Path, description: str) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ReviewDatasetError(f"{description} is missing or invalid JSON: {path}") from error
    if not isinstance(value, dict):
        raise ReviewDatasetError(f"{description} must contain a JSON object: {path}")
    return value


def load_files(path: Path) -> tuple[dict, dict]:
    reviewed = _read_json(path, "Reviewed dataset")
    snapshot = _read_json(path.parent / "snapshot.json", "Sibling snapshot")
    if reviewed.get("snapshot_hash") != canonical_hash(snapshot):
        raise ReviewDatasetError("Reviewed questions do not match the frozen snapshot")
    return reviewed, snapshot


def validate_legacy(reviewed: dict) -> list[dict]:
    """Retain the schema-v1 runner contract for reproducible historical runs."""
    if reviewed.get("schema_version") != 1 or not isinstance(reviewed.get("questions"), list):
        raise ReviewDatasetError("Unsupported reviewed question format")
    approved = [row for row in reviewed["questions"]
                if isinstance(row, dict) and row.get("review_status") == "approved"]
    if not approved:
        raise ReviewDatasetError("No questions have review_status=approved")
    ids = [row.get("id") for row in approved]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise ReviewDatasetError("Approved question IDs must be present and unique")
    return approved


def _paper_ids(question: ReviewedQuestionV2, snapshot: dict) -> list[str]:
    evidence_by_id = {row.get("evidence_id"): row for row in snapshot.get("evidence", [])
                      if isinstance(row, dict) and row.get("evidence_id")}
    derived = {
        str(row["paper_id"])
        for row in question.reference_evidence
        if isinstance(row, dict) and row.get("paper_id")
    }
    for evidence_id in question.generation_evidence_ids:
        evidence = evidence_by_id.get(evidence_id)
        if evidence and evidence.get("paper_id"):
            derived.add(str(evidence["paper_id"]))
    declared = set(question.paper_ids)
    if declared and derived and declared != derived:
        raise ReviewDatasetError(
            f"Question {question.id} paper_ids do not match its reference/generation evidence"
        )
    result = declared or derived
    known = {str(row["paper_id"]) for row in snapshot.get("papers", [])
             if isinstance(row, dict) and row.get("paper_id")}
    if not result or not result.issubset(known):
        raise ReviewDatasetError(f"Question {question.id} has missing or unknown paper_ids")
    return sorted(result)


def _expected_components(questions: list[ReviewedQuestionV2]) -> dict[str, tuple[str, ...]]:
    parent: dict[str, str] = {}

    def find(item: str) -> str:
        parent.setdefault(item, item)
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for question in questions:
        papers = question.paper_ids
        for paper in papers:
            find(paper)
        for paper in papers[1:]:
            union(papers[0], paper)
    components: dict[str, list[str]] = {}
    for paper in parent:
        components.setdefault(find(paper), []).append(paper)
    by_paper: dict[str, tuple[str, ...]] = {}
    for papers in components.values():
        component = tuple(sorted(papers))
        for paper in component:
            by_paper[paper] = component
    return by_paper


def component_id(papers: tuple[str, ...]) -> str:
    return "papers-" + sha256("\n".join(papers).encode()).hexdigest()[:12]


def validate_v2(reviewed: dict, snapshot: dict, *, require_splits: bool = True,
                selected_split: DatasetSplit | Literal["all"] = "all") -> tuple[dict, list[dict]]:
    try:
        dataset = ReviewedDatasetV2.model_validate(reviewed)
    except ValidationError as error:
        first = error.errors(include_url=False)[0]
        location = ".".join(str(part) for part in first["loc"])
        raise ReviewDatasetError(f"Invalid reviewed dataset field {location}: {first['msg']}") from None

    ids = [row.id for row in dataset.questions]
    if len(ids) != len(set(ids)):
        raise ReviewDatasetError("Question IDs must be unique")
    normalized = [re.sub(r"\W+", " ", row.question.casefold()).strip()
                  for row in dataset.questions if row.review_status == "approved"]
    if len(normalized) != len(set(normalized)):
        raise ReviewDatasetError("Approved question text must be unique after normalization")

    active_build_ids = {str(value) for value in snapshot.get("active_build_ids", [])}
    approved: list[ReviewedQuestionV2] = []
    for question in dataset.questions:
        papers = _paper_ids(question, snapshot)
        question.paper_ids = papers
        if question.review_status == "needs_review":
            continue
        if question.review is None or question.review.decision != question.review_status:
            raise ReviewDatasetError(
                f"Question {question.id} review metadata must match review_status"
            )
        if question.review_status == "rejected":
            continue
        if not question.review.original_sources_checked:
            raise ReviewDatasetError(f"Approved question {question.id} must have original_sources_checked=true")

        references = question.reference_evidence
        reference_builds = {str(row["build_id"]) for row in references
                            if isinstance(row, dict) and row.get("build_id")}
        if any(not isinstance(row, dict) or not row.get("point_id") or not row.get("paper_id")
               or not row.get("build_id") for row in references):
            raise ReviewDatasetError(
                f"Question {question.id} reference evidence needs point_id, paper_id and build_id"
            )
        if not reference_builds.issubset(active_build_ids):
            raise ReviewDatasetError(f"Question {question.id} references a build outside the frozen corpus")
        if question.kind == "unanswerable_candidate":
            if len(papers) != 1:
                raise ReviewDatasetError(
                    f"Unanswerable question {question.id} must target exactly one paper"
                )
            if references:
                raise ReviewDatasetError(f"Unanswerable question {question.id} cannot have reference evidence")
            if question.answerability_scope != "frozen_corpus" or not question.review.corpus_search_verified:
                raise ReviewDatasetError(
                    f"Approved unanswerable question {question.id} needs frozen_corpus scope and corpus verification"
                )
        else:
            if not references:
                raise ReviewDatasetError(f"Answerable question {question.id} needs reference evidence")
            expected_papers = 1 if question.kind == "single_paper" else 2
            if len(papers) != expected_papers:
                raise ReviewDatasetError(
                    f"Question {question.id} must be associated with {expected_papers} paper(s)"
                )
            reference_papers = {str(row["paper_id"]) for row in references}
            if len(reference_papers) != expected_papers:
                raise ReviewDatasetError(
                    f"Question {question.id} needs reference evidence from {expected_papers} paper(s)"
                )
        approved.append(question)

    if not approved:
        raise ReviewDatasetError("No questions have review_status=approved")
    by_paper = _expected_components(approved)
    for question in approved:
        expected_component = by_paper[question.paper_ids[0]]
        expected_group = component_id(expected_component)
        if require_splits:
            if dataset.split_policy is None or question.split is None or question.group_id is None:
                raise ReviewDatasetError("Schema-v2 approved questions require split assignment")
            if question.group_id != expected_group:
                raise ReviewDatasetError(f"Question {question.id} has an invalid paper-component group_id")
    if require_splits:
        paper_splits: dict[str, DatasetSplit] = {}
        for question in approved:
            for paper in question.paper_ids:
                previous = paper_splits.setdefault(paper, question.split)
                if previous != question.split:
                    raise ReviewDatasetError(f"Paper {paper} leaks across development and test splits")
        counts = Counter(question.split for question in approved)
        assert dataset.split_policy is not None
        if (counts["development"] != dataset.split_policy.development_questions
                or counts["test"] != dataset.split_policy.test_questions):
            raise ReviewDatasetError("Split-policy question counts do not match the assignments")
        actual_ratio = counts["test"] / len(approved)
        if abs(actual_ratio - dataset.split_policy.actual_test_ratio) > 1e-12:
            raise ReviewDatasetError("Split-policy actual_test_ratio does not match the assignments")

    selected = [row.model_dump(mode="json") for row in approved
                if selected_split == "all" or row.split == selected_split]
    if not selected:
        raise ReviewDatasetError(f"No approved questions are assigned to split={selected_split}")
    normalized_document = dataset.model_dump(mode="json")
    return normalized_document, selected


def assign_splits(reviewed: dict, snapshot: dict, *, test_ratio: float, seed: int) -> dict:
    if not 0 < test_ratio < 1:
        raise ReviewDatasetError("Test ratio must be greater than 0 and less than 1")
    normalized, approved_rows = validate_v2(reviewed, snapshot, require_splits=False)
    approved = [ReviewedQuestionV2.model_validate(row) for row in approved_rows]
    by_paper = _expected_components(approved)
    components: dict[tuple[str, ...], list[ReviewedQuestionV2]] = {}
    for question in approved:
        component = by_paper[question.paper_ids[0]]
        components.setdefault(component, []).append(question)
    if len(components) < 2:
        raise ReviewDatasetError(
            "A leakage-safe development/test split needs at least two disconnected paper groups"
        )

    total = len(approved)
    target_total = total * test_ratio
    kind_totals = Counter(row.kind for row in approved)

    def score(rows: list[ReviewedQuestionV2]) -> float:
        kinds = Counter(row.kind for row in rows)
        total_error = abs(len(rows) - target_total) / total
        kind_error = sum(
            abs(kinds[kind] - count * test_ratio) / count
            for kind, count in kind_totals.items()
        )
        return total_error + kind_error

    rng = random.Random(seed)
    candidates = list(components.items())
    rng.shuffle(candidates)
    candidates.sort(key=lambda item: len(item[1]), reverse=True)
    test_components: set[tuple[str, ...]] = set()
    test_rows: list[ReviewedQuestionV2] = []
    remaining = candidates[:]
    while remaining:
        best = min(remaining, key=lambda item: score(test_rows + item[1]))
        if test_rows and score(test_rows + best[1]) >= score(test_rows):
            break
        test_components.add(best[0])
        test_rows.extend(best[1])
        remaining.remove(best)
    if not test_components:
        best = min(candidates, key=lambda item: score(item[1]))
        test_components.add(best[0])
        test_rows.extend(best[1])
    if len(test_components) == len(components):
        worst = max(test_components, key=lambda component: len(components[component]))
        test_components.remove(worst)
        test_rows = [row for component in test_components for row in components[component]]

    assignments: dict[str, tuple[str, DatasetSplit]] = {}
    for component, questions in components.items():
        split: DatasetSplit = "test" if component in test_components else "development"
        group = component_id(component)
        for question in questions:
            assignments[question.id] = (group, split)
    for row in normalized["questions"]:
        if row["id"] in assignments:
            row["group_id"], row["split"] = assignments[row["id"]]
            row["paper_ids"] = next(item.paper_ids for item in approved if item.id == row["id"])
    test_count = len(test_rows)
    normalized["split_policy"] = {
        "name": "paper-components-v1",
        "seed": seed,
        "requested_test_ratio": test_ratio,
        "actual_test_ratio": test_count / total,
        "development_questions": total - test_count,
        "test_questions": test_count,
    }
    validate_v2(normalized, snapshot)
    return normalized


def write_json(path: Path, value: object) -> None:
    if path.exists():
        raise ReviewDatasetError(f"Output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise ReviewDatasetError(f"Output already exists: {path}") from error
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate a reviewed dataset; no service calls")
    validate.add_argument("--dataset", type=Path, required=True)
    validate.add_argument("--split", choices=["all", "development", "test"], default="all")
    split = commands.add_parser("assign-splits", help="Assign leakage-safe paper-group splits")
    split.add_argument("--dataset", type=Path, required=True)
    split.add_argument("--output", type=Path, required=True)
    split.add_argument("--test-ratio", type=float, default=0.25)
    split.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    try:
        reviewed, snapshot = load_files(args.dataset)
        if args.command == "validate":
            if reviewed.get("schema_version") == 1:
                if args.split != "all":
                    raise ReviewDatasetError("Schema-v1 datasets do not define splits")
                selected = validate_legacy(reviewed)
            else:
                _, selected = validate_v2(reviewed, snapshot, selected_split=args.split)
            print(json.dumps({"valid": True, "schema_version": reviewed.get("schema_version"),
                              "split": args.split, "approved_questions": len(selected)}, indent=2))
        else:
            result = assign_splits(reviewed, snapshot, test_ratio=args.test_ratio, seed=args.seed)
            write_json(args.output, result)
            print(json.dumps({"output": str(args.output), **result["split_policy"]}, indent=2))
    except ReviewDatasetError as error:
        print(f"Review dataset command failed: {error}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
