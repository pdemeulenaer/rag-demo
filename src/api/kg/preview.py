"""Read-only KG paper selection from a saved corpus snapshot; no config imports."""
from __future__ import annotations

from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from .contracts import Record, Text


DEFAULT_PILOT = Path(__file__).with_name("pilot.json")


class PilotPaper(Record):
    paper_id: UUID
    title: Text
    group: Text


class PilotSelection(Record):
    schema_version: Literal[1]
    name: Text
    papers: list[PilotPaper] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_papers(self):
        if len({paper.paper_id for paper in self.papers}) != len(self.papers):
            raise ValueError("Pilot contains duplicate papers")
        return self


class SnapshotPaper(BaseModel):
    paper_id: UUID
    build_id: UUID
    title: Text
    source: Literal["arxiv", "uploads"]
    collection: Text
    version: int = Field(ge=1)


class Snapshot(BaseModel):
    schema_version: Literal[1]
    corpus_fingerprint: Text
    active_build_ids: list[UUID]
    papers: list[SnapshotPaper] = Field(min_length=1)

    @model_validator(mode="after")
    def unambiguous_scope(self):
        if len({paper.paper_id for paper in self.papers}) != len(self.papers):
            raise ValueError("Snapshot contains duplicate paper identities")
        builds = [paper.build_id for paper in self.papers]
        if len(set(builds)) != len(builds):
            raise ValueError("Snapshot contains duplicate build identities")
        if not set(builds).issubset(self.active_build_ids):
            raise ValueError("Snapshot papers are outside its frozen build scope")
        return self


def preview(snapshot_path: Path, *, selection: Literal["pilot", "all"] = "pilot",
            pilot_path: Path = DEFAULT_PILOT) -> dict:
    if selection not in ("pilot", "all"):
        raise ValueError("Selection must be pilot or all")
    snapshot = Snapshot.model_validate_json(snapshot_path.read_text(encoding="utf-8"))
    available = {paper.paper_id: paper for paper in snapshot.papers}
    if selection == "all":
        groups = {paper.paper_id: "all" for paper in snapshot.papers}
        selected = sorted(snapshot.papers, key=lambda paper: str(paper.paper_id))
        name = "all-snapshot-papers"
    else:
        pilot = PilotSelection.model_validate_json(pilot_path.read_text(encoding="utf-8"))
        missing = [paper.title for paper in pilot.papers if paper.paper_id not in available]
        if missing:
            raise ValueError("Pilot papers missing from snapshot: " + "; ".join(missing))
        selected = [available[paper.paper_id] for paper in pilot.papers]
        groups = {paper.paper_id: paper.group for paper in pilot.papers}
        name = pilot.name
    return {
        "selection": name,
        "snapshot": str(snapshot_path),
        "corpus_fingerprint": snapshot.corpus_fingerprint,
        "scope": "frozen_snapshot_preview_not_live_catalogue",
        "papers_selected": len(selected),
        "papers_available": len(available),
        "model_calls": 0,
        "database_writes": 0,
        "graph_ready": False,
        "next_step": "Run make kg-prepare to verify/freeze full artifacts before paid kg-extract",
        "papers": [dict(paper.model_dump(mode="json"), group=groups[paper.paper_id])
                   for paper in selected],
    }
