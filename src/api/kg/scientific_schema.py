"""Scientific KG v2: role constraints and conservative numeric quarantine.

The v1 contracts remain immutable for read-only validation of earlier pilots.
These checks do not establish scientific truth or globally resolve aliases.
"""
import re
from typing import Literal

from pydantic import Field, model_validator

from . import contracts as v1


SCHEMA_VERSION = "scientific-kg-v2"
NUMERIC_KINDS = {"measurement", "upper_limit", "lower_limit", "simulation_result",
                 "selection_criterion", "model_parameter", "adopted_value"}


class Entity(v1.Entity):
    kind: Literal["astronomical_object", "stellar_population", "spatial_region",
                  "study", "analysis", "model", "physical_process",
                  "method", "dataset", "instrument", "author"]


class Observation(v1.Observation):
    kind: Literal["measurement", "upper_limit", "lower_limit", "simulation_result", "hypothesis",
                  "selection_criterion", "model_parameter", "adopted_value", "assumption",
                  "planned_analysis", "qualitative_finding", "method_description", "theoretical_result"]
    quantity_dimension: Literal["dimensionless", "length", "mass", "time", "inverse_time",
                                "angle", "temperature", "other", "unknown"] | None = None
    quality_flags: list[Literal[
        "ambiguous_source_numeric", "ambiguous_source_units", "ambiguous_source_uncertainty",
        "incomplete_evidence", "possible_source_conflict", "missing_quantity", "missing_value",
        "quantity_name_invalid", "numeric_format_ambiguous", "invalid_control_character",
        "unit_dimension_conflict",
    ]] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def conservative_quality_checks(self):
        flags = list(self.quality_flags)
        if self.kind in NUMERIC_KINDS:
            if not self.quantity:
                flags.append("missing_quantity")
            elif not any(character.isalpha() for character in self.quantity):
                flags.append("quantity_name_invalid")
            if not self.value_text:
                flags.append("missing_value")
            # Bracketed numeric fragments are ambiguous, not permission to guess
            # superscripts, uncertainties, units or footnote meaning.
            if any(re.search(r"\[[+−-]?\d", value or "")
                   for value in (self.value_text, self.uncertainty_text, self.unit_text)):
                flags.append("numeric_format_ambiguous")
            if self.quantity_dimension == "inverse_time" and self.unit_text:
                unit = re.sub(r"[\s*_]", "", self.unit_text).casefold()
                if unit in {"s", "sec", "second", "seconds", "min", "minute", "minutes", "h", "hr",
                            "hour", "hours", "d", "day", "days", "yr", "year", "years", "kyr", "myr", "gyr"}:
                    flags.append("unit_dimension_conflict")
        if any(any(ord(c) < 32 and c not in "\n\r\t" for c in value or "")
               for value in (self.statement, self.quantity, self.value_text, self.unit_text, self.uncertainty_text)):
            flags.append("invalid_control_character")
        self.quality_flags = list(dict.fromkeys(flags))
        return self

    @property
    def quarantined(self):
        return bool(self.quality_flags)


class Relationship(v1.Relationship):
    predicate: Literal["uses_method", "uses_dataset", "observed_with", "located_in",
                       "compares_with", "proposes_origin", "proposes_enrichment", "derived_from"]

    @model_validator(mode="after")
    def enrichment_is_explicit(self):
        if self.predicate == "proposes_enrichment" and self.epistemic_status != "hypothesis":
            raise ValueError("Proposed enrichment must remain a hypothesis")
        return self


# (allowed subjects, allowed objects). Observation is a role, not a model-emitted kind.
ROLE_RULES = {
    "uses_method": ({"study", "analysis", "model", "dataset", "observation"}, {"method", "model"}),
    "uses_dataset": ({"study", "analysis", "method", "model", "observation"}, {"dataset"}),
    "observed_with": ({"astronomical_object", "stellar_population", "spatial_region", "observation"}, {"instrument"}),
    "located_in": ({"astronomical_object", "stellar_population", "spatial_region"},
                   {"astronomical_object", "stellar_population", "spatial_region"}),
    "compares_with": ({"astronomical_object", "stellar_population", "analysis", "model", "dataset", "observation"},
                      {"astronomical_object", "stellar_population", "analysis", "model", "dataset", "observation"}),
    "proposes_origin": ({"astronomical_object", "stellar_population"}, {"astronomical_object", "stellar_population"}),
    "proposes_enrichment": ({"observation", "physical_process"}, {"physical_process", "astronomical_object", "stellar_population"}),
    "derived_from": ({"dataset", "model", "observation"}, {"dataset", "model"}),
}


def role_issues(entities, observations, relationships):
    roles = {record.id: record.kind for record in entities}
    roles.update({record.id: "observation" for record in observations})
    issues = []
    for index, relationship in enumerate(relationships):
        subjects, objects = ROLE_RULES[relationship.predicate]
        for field, allowed in (("subject_id", subjects), ("object_id", objects)):
            role = roles.get(getattr(relationship, field))
            if role is not None and role not in allowed:
                issues.append(dict(code="invalid_relationship_role", path=f"relationships.{index}.{field}",
                                   actual_role=role, allowed_roles=sorted(allowed), predicate=relationship.predicate))
    return issues


class ExtractionBatch(v1.ExtractionBatch):
    schema_version: Literal["scientific-kg-v2"] = SCHEMA_VERSION
    entities: list[Entity] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)

    @model_validator(mode="after")
    def semantic_roles(self):
        if role_issues(self.entities, self.observations, self.relationships):
            raise ValueError("Relationship endpoints have incompatible scientific roles")
        return self


def parse_batch(data):
    if data.get("schema_version") == "scientific-kg-v3":
        from .record_schema import ExtractionBatch as RecordBatch
        return RecordBatch.model_validate(data)
    if data.get("schema_version", v1.SCHEMA_VERSION) == v1.SCHEMA_VERSION:
        return v1.ExtractionBatch.model_validate(data)
    return ExtractionBatch.model_validate(data)
