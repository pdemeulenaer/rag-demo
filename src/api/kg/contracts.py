"""Scientific extraction records, independent of database/provider configuration.

Records are per-build assertions, not globally merged facts. These checks establish
identity and literal provenance, not scientific entailment or trusted aliases.
"""
from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


SCHEMA_VERSION = "scientific-kg-v1"
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceChunk(Record):
    """Existing full chunk loaded from a verified build artifact."""

    paper_id: UUID
    build_id: UUID
    collection: Text
    point_id: UUID
    source: Literal["arxiv", "uploads"]
    page_number: int = Field(ge=1)
    section_header: str | None = None
    text: Text


class EvidenceReference(Record):
    paper_id: UUID
    build_id: UUID
    collection: Text
    point_id: UUID
    source: Literal["arxiv", "uploads"]
    page_number: int = Field(ge=1)
    section_header: str | None = None
    quote: Text


Evidence = Annotated[list[EvidenceReference], Field(min_length=1)]


class Entity(Record):
    id: Text
    kind: Literal["astronomical_object", "method", "dataset", "instrument", "author"]
    name: Text
    # Candidates only: do not merge across builds until the resolver verifies them.
    aliases: list[Text] = Field(default_factory=list)
    evidence: Evidence


class Observation(Record):
    """An attributed assertion, preserving its original value and conditions."""

    id: Text
    subject_id: Text
    kind: Literal["measurement", "upper_limit", "lower_limit", "simulation_result", "hypothesis"]
    statement: Text
    quantity: Text | None = None
    value_text: Text | None = None
    unit_text: Text | None = None
    uncertainty_text: Text | None = None
    conditions: list[Text] = Field(default_factory=list)
    evidence: Evidence


class Relationship(Record):
    id: Text
    subject_id: Text
    predicate: Literal["uses_method", "uses_dataset", "observed_with", "located_in", "compares_with", "proposes_origin"]
    object_id: Text
    epistemic_status: Literal["reported", "hypothesis"]
    evidence: Evidence

    @model_validator(mode="after")
    def hypothesis_is_explicit(self):
        if self.predicate == "proposes_origin" and self.epistemic_status != "hypothesis":
            raise ValueError("Proposed origins must remain hypotheses")
        return self


class ExtractionBatch(Record):
    schema_version: Literal["scientific-kg-v1"] = SCHEMA_VERSION
    paper_id: UUID
    build_id: UUID
    extraction_model: Text
    extraction_revision: Text
    entities: list[Entity] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)

    @model_validator(mode="after")
    def identities_and_links(self):
        records = [*self.entities, *self.observations, *self.relationships]
        identifiers = [record.id for record in records]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Graph record IDs must be unique within a build")
        entities = {record.id for record in self.entities}
        nodes = entities | {record.id for record in self.observations}
        if any(record.subject_id not in entities for record in self.observations):
            raise ValueError("Observations must reference a declared entity")
        if any(record.subject_id not in nodes or record.object_id not in nodes
               for record in self.relationships):
            raise ValueError("Relationships must reference declared nodes")
        for record in records:
            for evidence in record.evidence:
                if evidence.paper_id != self.paper_id or evidence.build_id != self.build_id:
                    raise ValueError("Graph evidence must belong to the extraction build")
        return self

    def validate_sources(self, chunks: list[SourceChunk]) -> None:
        """Reject invented/stale IDs, metadata or quotes using supplied full chunks.

        The artifact loader must verify hashes and SQL-active/frozen scope
        BEFORE supplying chunks. This function does not establish that authority.
        """
        lookup = {(chunk.collection, chunk.point_id): chunk for chunk in chunks}
        if len(lookup) != len(chunks):
            raise ValueError("Duplicate source chunk identity")
        for record in [*self.entities, *self.observations, *self.relationships]:
            for evidence in record.evidence:
                chunk = lookup.get((evidence.collection, evidence.point_id))
                if chunk is None or any(getattr(chunk, key) != getattr(evidence, key)
                                        for key in ("paper_id", "build_id", "source",
                                                    "page_number", "section_header")):
                    raise ValueError("Graph evidence does not match a supplied source chunk")
                if evidence.quote not in chunk.text:
                    raise ValueError("Graph evidence quote is absent from its source chunk")
