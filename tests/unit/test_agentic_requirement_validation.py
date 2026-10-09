"""Offline structural plans: specific feedback without leaking rejected arguments."""
import pytest
from pydantic import ValidationError
from pydantic_core import PydanticCustomError

from src.api.rag.modes.agentic.contracts import (
    AnswerRequirement, InitialSearch, ParameterEffectNeed, RequirementValidationIssue,
)
from src.api.rag.modes.agentic.requirement_validation import (
    requirement_validation_issues, validate_parameter_effects,
)
from src.api.rag.modes.agentic.tools import define_requirements


def plan():
    requirements = [AnswerRequirement(id="r1", description="Report the measured flux."),
                    AnswerRequirement(id="r2", description="Report flux sensitivity to outer radius.")]
    searches = [InitialSearch(query="measured flux", requirement_indices=[1]),
                InitialSearch(query="flux outer radius dependence", requirement_indices=[2])]
    effects = [ParameterEffectNeed(requirement_index=2, baseline_requirement_index=1,
                                   parameter="outer radius")]
    return requirements, searches, effects


@pytest.mark.parametrize("mutation,code,field", [
    ("absent", "effect_declaration_missing", "parameter_effects"),
    ("duplicate", "duplicate_effect_requirement", "parameter_effects[1].requirement_index"),
    ("effect_index", "effect_index_out_of_range", "parameter_effects[0].requirement_index"),
    ("baseline_index", "baseline_index_out_of_range", "parameter_effects[0].baseline_requirement_index"),
    ("same_index", "baseline_effect_same_requirement", "parameter_effects[0].baseline_requirement_index"),
    ("parameter", "parameter_not_in_question", "parameter_effects[0].parameter"),
    ("effect_synthesis", "effect_not_factual", "parameter_effects[0].requirement_index"),
    ("null_baseline", "baseline_required", "parameter_effects[0].baseline_requirement_index"),
    ("baseline_synthesis", "baseline_not_factual", "parameter_effects[0].baseline_requirement_index"),
    ("missing_effect_search", "effect_search_missing", "parameter_effects[0].requirement_index"),
    ("missing_baseline_search", "baseline_search_missing", "parameter_effects[0].baseline_requirement_index"),
    ("same_query", "baseline_effect_same_query", "parameter_effects[0].requirement_index"),
])
def test_each_definition_rule_has_indexed_actionable_feedback(mutation, code, field):
    requirements, searches, effects = plan()
    if mutation == "absent":
        effects = []
    elif mutation == "duplicate":
        effects.append(effects[0].model_copy())
    elif mutation == "effect_index":
        effects[0].requirement_index = 3
    elif mutation == "baseline_index":
        effects[0].baseline_requirement_index = 3
    elif mutation == "same_index":
        effects[0].baseline_requirement_index = 2
    elif mutation == "parameter":
        effects[0].parameter = "PRIVATE_REJECTED_PARAMETER"
    elif mutation == "effect_synthesis":
        requirements[1].kind = "synthesis"
    elif mutation == "null_baseline":
        effects[0].baseline_requirement_index = None
    elif mutation == "baseline_synthesis":
        requirements[0].kind = "synthesis"
    elif mutation == "missing_effect_search":
        searches = searches[:1]
    elif mutation == "missing_baseline_search":
        searches = searches[1:]
    elif mutation == "same_query":
        searches[1].query = "  MEASURED    FLUX "
    with pytest.raises(ValidationError) as caught:
        validate_parameter_effects("Report measured flux and sensitivity to outer radius.",
                                   requirements, searches, effects)
    issues = requirement_validation_issues(caught.value, define_requirements.args_schema.model_fields)
    assert len(issues) == 1
    assert issues[0].code == code and issues[0].field == field
    assert issues[0].message and len(issues[0].message) <= 500
    assert "PRIVATE_REJECTED_PARAMETER" not in issues[0].model_dump_json()


@pytest.mark.parametrize("discovery_first", [False, True])
def test_valid_baseline_effect_plan_and_metadata_first_plan(discovery_first):
    requirements, searches, effects = plan()
    validate_parameter_effects("Report measured flux and sensitivity to outer radius.",
                               requirements, [] if discovery_first else searches, effects)


def test_effect_only_multiple_parameters_does_not_invent_baselines():
    requirements = [AnswerRequirement(id="r1", description="Temperature sensitivity."),
                    AnswerRequirement(id="r2", description="Density sensitivity.")]
    effects = [ParameterEffectNeed(requirement_index=1, parameter="temperature"),
               ParameterEffectNeed(requirement_index=2, parameter="density")]
    searches = [InitialSearch(query="temperature sensitivity", requirement_indices=[1]),
                InitialSearch(query="density sensitivity", requirement_indices=[2])]
    validate_parameter_effects("Report sensitivity to temperature and density.", requirements, searches, effects)


def test_all_errors_survive_instead_of_last_error_overwriting_others():
    requirements, searches, effects = plan()
    effects[0].baseline_requirement_index = None
    effects[0].parameter = "flux"  # Literal, but baseline is still missing.
    effects.append(ParameterEffectNeed(requirement_index=3, parameter="outer radius"))
    with pytest.raises(ValidationError) as caught:
        validate_parameter_effects("Report measured flux and sensitivity to outer radius.",
                                   requirements, searches, effects)
    issues = requirement_validation_issues(caught.value, define_requirements.args_schema.model_fields)
    assert {row.code for row in issues} == {"baseline_required", "effect_index_out_of_range"}


def test_feedback_never_copies_raw_exception_messages_input_or_context():
    secret = "PRIVATE_MUST_NOT_APPEAR"
    error = ValidationError.from_exception_data("Definition", [{
        "type": PydanticCustomError("parameter_not_in_question", secret, {"secret": secret}),
        "loc": ("parameter_effects", 0, "parameter"), "input": secret}, {
        "type": PydanticCustomError("value_error", secret, {"secret": secret}),
        "loc": ("initial_searches", 0, secret), "input": secret}])
    issues = requirement_validation_issues(error, define_requirements.args_schema.model_fields)
    assert "ORIGINAL question" in issues[0].message
    assert secret not in str([row.model_dump() for row in issues])
    assert issues[1].field == "initial_searches[0].<unknown_field>"


def test_historical_diagnostics_without_message_still_load():
    issue = RequirementValidationIssue(field="parameter_effects", code="invalid_effect_definition")
    assert issue.message is None
