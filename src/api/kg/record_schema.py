"""KG v3 keeps structurally typed records; invalid links are held per record.

Historical v1/v2 validation stays unchanged. Duplicate IDs and source identity
violations still invalidate the entire batch; quarantine never repairs a record.
"""
from typing import Literal

from pydantic import Field, model_validator

from . import contracts as v1
from .scientific_schema import Entity, Observation, Relationship

SCHEMA_VERSION = "scientific-kg-v3"


class ExtractionBatch(v1.ExtractionBatch):
    schema_version: Literal["scientific-kg-v3"] = SCHEMA_VERSION
    entities: list[Entity] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)

    @model_validator(mode="after")
    def identities_and_links(self):
        # Override only v1's chunk-wide link rejection. Unknown links and wrong
        # roles remain intact in records and are excluded by quarantine_report.
        records = [*self.entities, *self.observations, *self.relationships]
        ids = [record.id for record in records]
        if len(ids) != len(set(ids)):
            raise ValueError("Graph record IDs must be unique within a build")
        for record in records:
            for evidence in record.evidence:
                if evidence.paper_id != self.paper_id or evidence.build_id != self.build_id:
                    raise ValueError("Graph evidence must belong to the extraction build")
        return self
