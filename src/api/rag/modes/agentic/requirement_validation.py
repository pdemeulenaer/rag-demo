"""Definition checks and safe feedback for the existing native tool correction.

Guidance is application-owned, never copied from exception messages or model inputs.
These are plan-structure checks, not scientific entailment or a new planner protocol.
"""
from pydantic import ValidationError
from pydantic_core import PydanticCustomError

from src.api.rag.modes.agentic.contracts import (
    AnswerRequirement, InitialSearch, ParameterEffectNeed, RequirementValidationIssue,
)
from src.api.rag.modes.agentic.effect_evidence import literal_span
from src.api.rag.question_coverage import (
    original_question_parts, requests_baseline_and_effect, requests_parameter_effect,
)


_GUIDANCE = {
    "missing": "Supply the required field at this path in the corrected definition.",
    "internal_tool_requirement": "Replace the standalone protocol label with a user-requested scientific fact.",
    "effect_declaration_missing": "Declare the requested varied input in parameter_effects and link its effect requirement_index.",
    "duplicate_effect_requirement": "Give each declared parameter a unique effect requirement_index; do not reuse an effect entry.",
    "effect_index_out_of_range": "Set requirement_index to the 1-based index of an existing effect description.",
    "baseline_index_out_of_range": "Set baseline_requirement_index to the 1-based index of an existing baseline description.",
    "baseline_effect_same_requirement": "Split baseline and effect into two descriptions and use their different 1-based indices.",
    "parameter_not_in_question": "Copy a short contiguous parameter name from the ORIGINAL question, retaining its qualifiers; do not paraphrase or substitute the measured output.",
    "effect_not_factual": "The reported parameter effect needs factual evidence; remove its index from synthesis_indices or associate a focused initial search.",
    "baseline_required": "The question asks BOTH a measurement and its parameter effect. Add a separate baseline description and use its index instead of null, with separate focused searches.",
    "baseline_not_factual": "The requested baseline needs factual evidence; remove its index from synthesis_indices or associate a focused initial search.",
    "effect_search_missing": "Add a focused initial search linked to the effect requirement_index, naming the varied parameter and outcome change/dependence.",
    "baseline_search_missing": "Add a focused initial search linked to baseline_requirement_index for the measurement itself.",
    "baseline_effect_same_query": "Baseline and effect searches are identical after confirmed titles/IDs are removed. Keep those identities in filters; use different content queries for the measurement and parameter-dependent outcome. Changing filters, retrieval mode or limit alone does not separate these facts.",
}


def validate_parameter_effects(question: str, requirements: list[AnswerRequirement],
                               searches: list[InitialSearch], effects: list[ParameterEffectNeed]) -> None:
    """Validate the normalized plan without silently rewriting requirements or queries."""
    errors = []

    def reject(code, loc):
        errors.append({"type": PydanticCustomError(code, _GUIDANCE[code]),
                       "loc": loc, "input": None})

    if requests_parameter_effect(question) and not effects:
        reject("effect_declaration_missing", ("parameter_effects",))
    seen = set()
    for index, effect in enumerate(effects):
        path = ("parameter_effects", index)
        target, baseline = effect.requirement_index, effect.baseline_requirement_index
        if target in seen:
            reject("duplicate_effect_requirement", (*path, "requirement_index"))
        seen.add(target)
        if target > len(requirements):
            reject("effect_index_out_of_range", (*path, "requirement_index"))
            continue
        if baseline is not None and baseline > len(requirements):
            reject("baseline_index_out_of_range", (*path, "baseline_requirement_index"))
            continue
        if baseline == target:
            reject("baseline_effect_same_requirement", (*path, "baseline_requirement_index"))
            continue
        if not literal_span(question, effect.parameter):
            reject("parameter_not_in_question", (*path, "parameter"))
        if requirements[target - 1].kind != "fact":
            reject("effect_not_factual", (*path, "requirement_index"))
        if baseline is None:
            if any(literal_span(part, effect.parameter) and requests_baseline_and_effect(part)
                   for _, part in original_question_parts(question)):
                reject("baseline_required", (*path, "baseline_requirement_index"))
            continue
        if requirements[baseline - 1].kind != "fact":
            reject("baseline_not_factual", (*path, "baseline_requirement_index"))
        # Empty plans allow metadata discovery first. Otherwise both facts must
        # have distinct normalized content queries, not just different filters.
        if searches:
            effect_queries = {" ".join(row.query.casefold().split()) for row in searches
                              if target in row.requirement_indices}
            baseline_queries = {" ".join(row.query.casefold().split()) for row in searches
                                if baseline in row.requirement_indices}
            if not effect_queries:
                reject("effect_search_missing", (*path, "requirement_index"))
            if not baseline_queries:
                reject("baseline_search_missing", (*path, "baseline_requirement_index"))
            if effect_queries and baseline_queries and not any(
                    left != right for left in effect_queries for right in baseline_queries):
                reject("baseline_effect_same_query", (*path, "requirement_index"))
    if errors:
        raise ValidationError.from_exception_data("ParameterEffectDefinition", errors)


def requirement_validation_issues(error: ValidationError, top_fields) -> list[RequirementValidationIssue]:
    """Whitelist schema paths and static guidance; ignore raw messages/input/context."""
    issues = []
    for item in error.errors(include_input=False, include_context=False, include_url=False)[:20]:
        loc = item.get("loc", ())
        parts = []
        for index, segment in enumerate(loc):
            if index == 0 and segment in top_fields:
                parts.append(segment)
            elif (type(segment) is int and 0 <= segment <= 1000 and parts and (
                  index == 1 and loc[0] in {"descriptions", "initial_searches", "synthesis_indices", "parameter_effects"}
                  or index == 3 and loc[0] == "initial_searches" and loc[2] in {
                      "requirement_indices", "build_ids", "paper_ids"})):
                parts[-1] += f"[{segment}]"
            elif (index == 2 and loc[0] == "initial_searches"
                  and type(loc[1]) is int and segment in InitialSearch.model_fields):
                parts.append(segment)
            elif (index == 2 and loc[0] == "parameter_effects"
                  and type(loc[1]) is int and segment in ParameterEffectNeed.model_fields):
                parts.append(segment)
            else:
                parts.append("<unknown_field>")
                break
        code = item.get("type", "invalid")
        issues.append(RequirementValidationIssue(
            field=".".join(parts) or "<root>", code=code,
            message=_GUIDANCE.get(code, "Fix the field at this path to match its native tool schema.")))
    return issues
