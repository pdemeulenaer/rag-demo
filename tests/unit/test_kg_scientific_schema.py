"""Role and numeric-quality regressions independent of model/configuration imports."""
from copy import deepcopy
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.api.kg.scientific_schema import ExtractionBatch, Observation, ROLE_RULES, parse_batch


EVIDENCE = dict(paper_id=str(UUID(int=1)), build_id=str(UUID(int=2)), collection="test",
                point_id=str(UUID(int=3)), source="arxiv", page_number=1, section_header="Results",
                quote="A source assertion.")


def entity(identifier, kind):
    return dict(id=identifier, kind=kind, name=identifier, aliases=[], evidence=[deepcopy(EVIDENCE)])


def batch(subject_kind, object_kind, predicate, epistemic_status="reported"):
    entities = [entity("subject", subject_kind), entity("object", object_kind)]
    return dict(paper_id=EVIDENCE["paper_id"], build_id=EVIDENCE["build_id"],
        extraction_model="test", extraction_revision="test",
        entities=entities, observations=[], relationships=[dict(
            id="relation", subject_id="subject", object_id="object", predicate=predicate,
            epistemic_status=epistemic_status, evidence=[deepcopy(EVIDENCE)])])


@pytest.mark.parametrize("subject_kind,object_kind,predicate", [
    ("stellar_population", "dataset", "located_in"),
    ("astronomical_object", "dataset", "located_in"),
    ("method", "dataset", "located_in"),
    ("dataset", "astronomical_object", "uses_dataset"),
    ("study", "author", "uses_method"),
    ("method", "stellar_population", "uses_method"),
    ("dataset", "astronomical_object", "observed_with"),
    ("analysis", "physical_process", "observed_with"),
    ("astronomical_object", "method", "uses_method"),
    ("astronomical_object", "physical_process", "proposes_enrichment"),
])
def test_incompatible_roles_are_rejected(subject_kind, object_kind, predicate):
    raw = batch(subject_kind, object_kind, predicate,
                "hypothesis" if predicate == "proposes_enrichment" else "reported")
    with pytest.raises(ValidationError, match="incompatible scientific roles"):
        ExtractionBatch.model_validate(raw)


@pytest.mark.parametrize("subject_kind,object_kind,predicate", [
    ("study", "dataset", "uses_dataset"), ("analysis", "method", "uses_method"),
    ("dataset", "model", "uses_method"), ("model", "dataset", "uses_dataset"),
    ("stellar_population", "instrument", "observed_with"),
    ("astronomical_object", "spatial_region", "located_in"),
    ("stellar_population", "stellar_population", "compares_with"),
    ("dataset", "dataset", "derived_from"),
    ("physical_process", "stellar_population", "proposes_enrichment"),
    ("astronomical_object", "astronomical_object", "proposes_origin"),
])
def test_meaningful_roles_are_accepted(subject_kind, object_kind, predicate):
    status = "hypothesis" if predicate.startswith("proposes_") else "reported"
    assert ExtractionBatch.model_validate(batch(subject_kind, object_kind, predicate, status)).schema_version == "scientific-kg-v2"


def observation(**values):
    return Observation(id="obs", subject_id="object", statement="A result.",
                       evidence=[deepcopy(EVIDENCE)], **values)


@pytest.mark.parametrize("kind", ["selection_criterion", "model_parameter", "adopted_value", "simulation_result"])
def test_non_measurement_numeric_kinds_preserve_values_and_conditions(kind):
    record = observation(kind=kind, quantity="selection_radius", value_text="2", unit_text="degrees",
                         quantity_dimension="angle", conditions=["selected sample, not intrinsic object radius"])
    assert not record.quarantined
    assert record.kind == kind and record.conditions


@pytest.mark.parametrize("kind", ["planned_analysis", "assumption", "qualitative_finding", "method_description", "theoretical_result", "hypothesis"])
def test_non_numeric_assertions_need_not_invent_values(kind):
    record = observation(kind=kind)
    assert record.value_text is None and not record.quarantined


@pytest.mark.parametrize("values,flag", [
    (dict(kind="measurement", value_text="3.27"), "missing_quantity"),
    (dict(kind="measurement", quantity="distance"), "missing_value"),
    (dict(kind="measurement", quantity="2", value_text="2"), "quantity_name_invalid"),
    (dict(kind="measurement", quantity="distance", value_text="3.27", uncertainty_text="\x0614"), "invalid_control_character"),
    (dict(kind="measurement", quantity="rate", value_text="6 _._ 91[+0] _−_ 0 _[.] ._[82] 23"), "numeric_format_ambiguous"),
    (dict(kind="measurement", quantity="rate", value_text="6.91", unit_text="Myr", quantity_dimension="inverse_time"), "unit_dimension_conflict"),
    (dict(kind="measurement", quantity="distance", value_text="3.27", quality_flags=["ambiguous_source_uncertainty"]), "ambiguous_source_uncertainty"),
])
def test_numeric_ambiguity_is_quarantined_not_repaired(values, flag):
    record = observation(**values)
    assert record.quarantined and flag in record.quality_flags
    assert record.value_text == values.get("value_text")


def test_clear_rate_and_asymmetric_uncertainty_are_preserved():
    record = observation(kind="measurement", quantity="birthrate", value_text="6.91",
                         uncertainty_text="+0.82/-0.23", unit_text="Myr−1", quantity_dimension="inverse_time")
    assert not record.quarantined
    assert record.uncertainty_text == "+0.82/-0.23"


def test_flags_idempotent_on_revalidation():
    record = observation(kind="measurement", quantity="rate", value_text="6[+0]", quality_flags=["possible_source_conflict"])
    again = Observation.model_validate(record.model_dump())
    assert record.quality_flags == again.quality_flags


def test_legacy_loader_does_not_silently_reclassify_records():
    raw = batch("astronomical_object", "dataset", "located_in")
    raw["schema_version"] = "scientific-kg-v1"
    assert parse_batch(raw).schema_version == "scientific-kg-v1"
    raw["schema_version"] = "scientific-kg-v2"
    with pytest.raises(ValidationError):
        parse_batch(raw)


def test_observation_can_be_source_of_enrichment_hypothesis():
    raw = batch("study", "physical_process", "proposes_enrichment", "hypothesis")
    raw["observations"] = [observation(kind="qualitative_finding").model_dump()]
    raw["observations"][0]["subject_id"] = "subject"
    raw["relationships"][0]["subject_id"] = "obs"
    assert ExtractionBatch.model_validate(raw).relationships[0].epistemic_status == "hypothesis"
    raw["relationships"][0]["epistemic_status"] = "reported"
    with pytest.raises(ValidationError, match="hypothesis"):
        ExtractionBatch.model_validate(raw)
