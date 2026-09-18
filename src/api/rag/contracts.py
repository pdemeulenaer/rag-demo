"""Shared contracts for every RAG retrieval strategy.

PostgreSQL selects the allowed builds; Qdrant may only return evidence from that
explicit scope. Keeping this contract independent from an agent framework lets
Vanilla, Hybrid, Hybrid + Rerank, Agentic and future KG modes share the same safety boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from qdrant_client.models import FieldCondition, Filter, MatchAny


ScopeKind = Literal["active", "frozen"]


@dataclass(frozen=True)
class ScopedBuild:
    """Identity needed to validate (and, for legacy points, recover) provenance."""

    build_id: str
    paper_id: str | None = None
    point_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalScope:
    """An immutable, explicit corpus boundary for one retrieval operation."""

    collection: str
    build_ids: tuple[str, ...]
    kind: ScopeKind = "active"
    paper_ids: tuple[str, ...] = ()
    builds: tuple[ScopedBuild, ...] = ()
    filter_override: Filter | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        collection = self.collection.strip()
        build_ids = tuple(dict.fromkeys(str(value) for value in self.build_ids if str(value)))
        paper_ids = tuple(dict.fromkeys(str(value) for value in self.paper_ids if str(value)))
        if not collection:
            raise ValueError("Retrieval scope requires a collection")
        if not build_ids:
            raise ValueError("Retrieval scope requires at least one build ID")
        unknown = {build.build_id for build in self.builds}.difference(build_ids)
        if unknown:
            raise ValueError("Scoped build metadata contains an unapproved build ID")
        object.__setattr__(self, "collection", collection)
        object.__setattr__(self, "build_ids", build_ids)
        object.__setattr__(self, "paper_ids", paper_ids)

    @classmethod
    def from_builds(cls, collection: str, rows: list[dict], *, kind: ScopeKind = "active",
                    filter_override: Filter | None = None) -> "RetrievalScope":
        from src.api.papers.consistency import expected_ids

        scoped = tuple(ScopedBuild(
            build_id=str(row["id"]), paper_id=str(row["paper_id"]) if row.get("paper_id") else None,
            point_ids=tuple(expected_ids(row)),
        ) for row in rows)
        return cls(collection=collection, build_ids=tuple(row.build_id for row in scoped),
                   kind=kind, builds=scoped, filter_override=filter_override)

    def qdrant_filter(self) -> Filter:
        build_filter = self.filter_override or Filter(must=[
            FieldCondition(key="build_id", match=MatchAny(any=list(self.build_ids)))
        ])
        if not self.paper_ids:
            return build_filter
        return Filter(must=[build_filter, FieldCondition(
            key="paper_id", match=MatchAny(any=list(self.paper_ids)))])

    def identity_for_point(self, point_id: str) -> tuple[str | None, str | None]:
        wanted = str(point_id)
        for build in self.builds:
            if wanted in build.point_ids:
                return build.build_id, build.paper_id
        return None, None


class PaperMatch(BaseModel):
    """A PostgreSQL catalogue result suitable for a retrieval plan."""

    model_config = ConfigDict(extra="forbid")

    paper_id: str
    build_id: str
    source: str
    source_id: str
    collection: str
    version: int
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    abstract: str | None = None
    metadata: dict = Field(default_factory=dict)


class EvidenceChunk(BaseModel):
    """Evidence returned by any vector, graph or expansion tool."""

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    collection: str
    build_id: str
    paper_id: str
    title: str | None = None
    arxiv_id: str | None = None
    paper_version: int | None = None
    source_url: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    page: int | None = None
    section_header: str | None = None
    content_kind: str | None = None
    chunk_index: int | None = None
    score: float | None = None
    rerank_score: float | None = None
    type: str = "text"
    image_path: str | None = None
    caption: str | None = None
