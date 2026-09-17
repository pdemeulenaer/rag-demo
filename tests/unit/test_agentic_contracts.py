import copy

import pytest
from pydantic import ValidationError

from src.api.rag.modes.agentic.contracts import (
    AgentBudget,
    AgentPlan,
    BudgetUsage,
    GetNeighborsAction,
    SearchChunksAction,
    StopReason,
    SufficiencyDecision,
    action_fingerprint,
    budget_stop_reason,
    validate_decision_for_plan,
)


def plan_data():
    return {
        "schema_version": 1,
        "question_scope": "cross_paper",
        "plan_summary": "Compare the reported cluster mass estimates in two papers.",
        "evidence_needs": [
            {"need_id": "mass_a", "subquestion": "What mass does paper A report?",
             "success_criteria": "A stated mass with its source chunk.",
             "target_paper_ids": ["paper-a"]},
            {"need_id": "mass_b", "subquestion": "What mass does paper B report?",
             "success_criteria": "A stated mass with its source chunk.",
             "target_paper_ids": ["paper-b"]},
        ],
        "initial_actions": [
            {"action_id": "search_a", "need_id": "mass_a", "tool": "search_chunks",
             "query": "reported cluster mass", "retrieval_mode": "hybrid",
             "build_ids": ["build-a"], "paper_ids": ["paper-a"], "limit": 8},
            {"action_id": "search_b", "need_id": "mass_b", "tool": "search_chunks",
             "query": "reported cluster mass", "retrieval_mode": "hybrid",
             "build_ids": ["build-b"], "paper_ids": ["paper-b"], "limit": 8},
        ],
    }


def assessments(*, second_satisfied=False):
    return [
        {"need_id": "mass_a", "satisfied": True, "evidence_ids": ["point-a"],
         "missing_evidence": None},
        {"need_id": "mass_b", "satisfied": second_satisfied,
         "evidence_ids": ["point-b"] if second_satisfied else [],
         "missing_evidence": None if second_satisfied else "A directly stated mass."},
    ]


def test_plan_parses_only_declared_read_only_actions():
    plan = AgentPlan.model_validate(plan_data())
    assert plan.question_scope.value == "cross_paper"
    assert all(isinstance(action, SearchChunksAction) for action in plan.initial_actions)

    invalid = copy.deepcopy(plan_data())
    invalid["initial_actions"][0]["tool"] = "delete_paper"
    with pytest.raises(ValidationError):
        AgentPlan.model_validate(invalid)


@pytest.mark.parametrize("mutation", ["duplicate_need", "duplicate_action", "unknown_need"])
def test_plan_rejects_ambiguous_or_unbound_identifiers(mutation):
    value = copy.deepcopy(plan_data())
    if mutation == "duplicate_need":
        value["evidence_needs"][1]["need_id"] = "mass_a"
    elif mutation == "duplicate_action":
        value["initial_actions"][1]["action_id"] = "search_a"
    else:
        value["initial_actions"][1]["need_id"] = "unknown"
    with pytest.raises(ValidationError):
        AgentPlan.model_validate(value)


def test_contracts_forbid_extra_fields_and_unbounded_actions():
    value = copy.deepcopy(plan_data())
    value["hidden_reasoning"] = "not part of the contract"
    with pytest.raises(ValidationError, match="Extra inputs"):
        AgentPlan.model_validate(value)
    with pytest.raises(ValidationError):
        GetNeighborsAction.model_validate({
            "action_id": "expand", "need_id": "mass_a", "tool": "get_neighbors",
            "build_id": "build-a", "paper_id": "paper-a", "chunk_index": 2,
            "before": 6, "after": 1,
        })


def test_plan_provider_schema_is_strict_and_has_no_optional_omissions():
    schema = AgentPlan.model_json_schema()
    objects = [schema, *(value for value in schema.get("$defs", {}).values()
                         if "properties" in value)]
    for value in objects:
        assert value["additionalProperties"] is False
        assert set(value["properties"]) == set(value["required"])


def test_sufficiency_decision_enforces_continue_synthesize_and_abstain_invariants():
    continuation = SufficiencyDecision.model_validate({
        "schema_version": 1, "decision": "continue",
        "summary": "Paper B still needs direct evidence.",
        "assessments": assessments(),
        "next_actions": [{
            "action_id": "expand_b", "need_id": "mass_b", "tool": "get_neighbors",
            "build_id": "build-b", "paper_id": "paper-b", "chunk_index": 4,
            "before": 1, "after": 2,
        }],
        "stop_reason": None,
    })
    assert continuation.decision == "continue"

    synthesis = SufficiencyDecision.model_validate({
        "schema_version": 1, "decision": "synthesize", "summary": "Both masses found.",
        "assessments": assessments(second_satisfied=True), "next_actions": [],
        "stop_reason": "sufficient",
    })
    assert synthesis.stop_reason == StopReason.SUFFICIENT

    invalid = synthesis.model_dump(mode="json")
    invalid["assessments"][1]["satisfied"] = False
    invalid["assessments"][1]["evidence_ids"] = []
    invalid["assessments"][1]["missing_evidence"] = "Mass missing."
    with pytest.raises(ValidationError, match="Synthesis requires"):
        SufficiencyDecision.model_validate(invalid)


def test_decision_must_cover_the_plan_and_actions_must_reference_its_needs():
    plan = AgentPlan.model_validate(plan_data())
    decision = SufficiencyDecision.model_validate({
        "schema_version": 1, "decision": "abstain", "summary": "Evidence remained incomplete.",
        "assessments": assessments(), "next_actions": [], "stop_reason": "max_rounds",
    })
    validate_decision_for_plan(plan, decision, {"point-a"})

    changed = decision.model_copy(update={"assessments": decision.assessments[:1]})
    with pytest.raises(ValueError, match="assess every"):
        validate_decision_for_plan(plan, changed)

    with pytest.raises(ValueError, match="unavailable evidence"):
        validate_decision_for_plan(plan, decision, set())


def test_action_fingerprint_ignores_planner_ids_but_not_tool_arguments():
    first = SearchChunksAction.model_validate(plan_data()["initial_actions"][0])
    duplicate = first.model_copy(update={"action_id": "retry", "need_id": "mass_b"})
    changed = first.model_copy(update={"query": "cluster tidal mass"})
    assert action_fingerprint(first) == action_fingerprint(duplicate)
    assert action_fingerprint(first) != action_fingerprint(changed)


@pytest.mark.parametrize(("usage", "reason"), [
    (BudgetUsage(rounds=3), StopReason.MAX_ROUNDS),
    (BudgetUsage(tool_calls=12), StopReason.TOOL_CALL_BUDGET),
    (BudgetUsage(evidence_chunks=30), StopReason.EVIDENCE_BUDGET),
    (BudgetUsage(elapsed_seconds=120), StopReason.TIME_BUDGET),
    (BudgetUsage(planner_tokens=6000), StopReason.TOKEN_BUDGET),
    (BudgetUsage(rounds=1, tool_calls=2), None),
])
def test_budget_stop_reason_is_deterministic(usage, reason):
    assert budget_stop_reason(AgentBudget(), usage) == reason
