from unittest.mock import Mock
from types import SimpleNamespace
from threading import Barrier, Event, Lock

import pytest

from langchain_core.messages import AIMessage

from src.api.rag.contracts import EvidenceChunk, RetrievalScope, ScopedBuild
from src.api.rag.modes.agentic.contracts import AgentBudget, StopReason
from src.api.rag.modes.agentic.executor import run_agentic
from src.api.rag.modes.agentic.policies import (
    action_fingerprint, narrow_scope, observed_section_header, scoped_requirement_query,
)


def scope():
    return RetrievalScope("papers", ("build-1",), builds=(
        ScopedBuild("build-1", "paper-1"),
    ))


def chunk(point_id="point-1"):
    return EvidenceChunk(
        id=point_id, text="The cluster mass is reported as evidence.",
        collection="papers", build_id="build-1", paper_id="paper-1",
        title="Cluster paper", page=3, section_header="Results", chunk_index=4,
    )


def call(name, arguments, call_id):
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": arguments, "id": call_id,
                     "type": "tool_call"}],
        usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    )


def search(call_id="call_search", query="cluster mass", need_id="r1"):
    return call("search_chunks", {
        "need_id": need_id,
        "query": query, "retrieval_mode": "hybrid",
        "build_ids": [], "paper_ids": [], "limit": 5,
    }, call_id)


def finish(call_id="call_finish"):
    return call("finish_with_evidence", {
        "summary": "Direct evidence was found.", "question_scope": "direct",
    }, call_id)


class FakeToolCallingModel:
    def __init__(self, responses, requirements=("Report the mass.",), *, define=True,
                 initial_searches=(), synthesis_indices=(), parameter_effects=()):
        self.responses = ([call("define_requirements", {
            "descriptions": list(requirements), "initial_searches": list(initial_searches),
            "synthesis_indices": list(synthesis_indices), "parameter_effects": list(parameter_effects)},
                                "define")] if define else []) + list(responses)
        self.bound_tools = []
        self.bind_options = []
        self.seen_messages = []

    def bind_tools(self, tools, **kwargs):
        self.bind_options.append(kwargs)
        self.bound_tools = tools
        return self

    def invoke(self, messages):
        self.seen_messages.append(list(messages))
        return self.responses.pop(0)


def effect_definition(*, combined=False):
    return call("define_requirements", {
        "descriptions": (["Report baseline and outer radius dependence."] if combined else
                         ["Report the baseline flux.", "Report flux sensitivity to outer radius."]),
        "initial_searches": [], "synthesis_indices": [],
        "parameter_effects": [{"requirement_index": 1 if combined else 2,
                               "baseline_requirement_index": 1, "parameter": "outer radius"}],
    }, "definition-bad" if combined else "definition-good")


def effect_finish(*, context_id="effect", parameter="outer radius", outcome="flux decreases",
                  kind="reported_change", call_id="finish-effect"):
    return call("finish_with_evidence", {
        "summary": "The parameter response was found.", "question_scope": "direct",
        "effect_evidence": [{"need_id": "r2", "context_id": context_id,
                             "parameter_quote": parameter, "outcome_quote": outcome,
                             "outcome_kind": kind}],
    }, call_id)


@pytest.mark.parametrize("invalid", [
    effect_finish(parameter="inner radius", outcome="flux is unchanged", kind="reported_no_change"),
    effect_finish(parameter="outer radius", outcome="flux is high", kind="baseline"),
    effect_finish(parameter="outer radius", outcome="two values were tested", kind="settings_only"),
    effect_finish(context_id="not-retrieved"),
    effect_finish(outcome="invented missing result"),
])
def test_effect_finish_rejects_wrong_parameter_baseline_and_settings_then_recovers(monkeypatch, invalid):
    baseline = chunk("baseline").model_copy(update={"text": "The baseline flux is high."})
    wrong = chunk("wrong").model_copy(update={"text": (
        "The outer radius has two values were tested; flux is high. The inner radius varies; flux is unchanged.")})
    effect = chunk("effect").model_copy(update={"text": "Increasing the outer radius means flux decreases."})
    # First finish has literal but semantically wrong evidence (or an unavailable ID).
    invalid = invalid.model_copy(deep=True)
    if invalid.tool_calls[0]["args"]["effect_evidence"][0]["context_id"] == "effect":
        invalid.tool_calls[0]["args"]["effect_evidence"][0]["context_id"] = "wrong"
    lookup = Mock(side_effect=[[baseline, wrong], [effect]])
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_chunk_search", lookup)
    model = FakeToolCallingModel([
        effect_definition(), search(), invalid,
        search("focused-recovery", "outer radius flux dependence change", "r2"), effect_finish(),
    ], define=False)
    result = run_agentic("Report baseline flux and sensitivity to outer radius.", client=Mock(),
        catalogue=Mock(), scope=scope(), embed=Mock(return_value=[1.0]), model=model,
        budget=AgentBudget(max_rounds=2))
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert result.execution.rounds == 2 and result.execution.tool_calls == 2
    assert [row["status"] for row in result.execution.effect_finish_checks] == ["rejected", "accepted"]
    assert result.execution.parameter_effects[0].baseline_requirement_index == 1
    assert result.execution.actions[-1].query == "outer radius flux dependence change"
    feedback = [message for messages in model.seen_messages for message in messages
                if getattr(message, "name", "") == "finish_with_evidence"]
    assert any("effect_evidence_incomplete" in message.content for message in feedback)


def test_combined_baseline_and_effect_definition_uses_existing_single_correction(monkeypatch):
    effect = chunk("effect").model_copy(update={"text": "As outer radius increases, flux decreases."})
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_chunk_search", Mock(return_value=[effect]))
    model = FakeToolCallingModel([effect_definition(combined=True), effect_definition(),
                                 search(), effect_finish()], define=False)
    result = run_agentic("Report baseline flux and sensitivity to outer radius.", client=Mock(),
        catalogue=Mock(), scope=scope(), embed=Mock(return_value=[1.0]), model=model)
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert result.execution.requirement_correction_attempts == 1
    issue = result.execution.requirement_validation_failures[0].issues[0]
    assert issue.field == "parameter_effects[0].baseline_requirement_index"
    assert issue.code == "baseline_effect_same_requirement"
    assert "two descriptions" in issue.message
    assert len(result.requirements) == 2


def test_null_baseline_cannot_hide_coordinated_measurement_and_effect(monkeypatch):
    effect = chunk("effect").model_copy(update={"text": "As outer radius increases, flux decreases."})
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_chunk_search", Mock(return_value=[effect]))
    combined = effect_definition(combined=True)
    combined.tool_calls[0]["args"]["parameter_effects"][0]["baseline_requirement_index"] = None
    model = FakeToolCallingModel([combined, effect_definition(), search(), effect_finish()], define=False)
    result = run_agentic("Report the measured flux and sensitivity to outer radius.", client=Mock(),
        catalogue=Mock(), scope=scope(), embed=Mock(return_value=[1.0]), model=model)
    assert result.execution.requirement_correction_attempts == 1
    issue = result.execution.requirement_validation_failures[0].issues[0]
    assert issue.code == "baseline_required"
    assert issue.field == "parameter_effects[0].baseline_requirement_index"
    assert "instead of null" in issue.message
    assert len(result.requirements) == 2
    assert result.requirements[1].effect_parameters == ["outer radius"]
    assert result.execution.stop_reason == StopReason.SUFFICIENT


def test_effect_only_request_does_not_acquire_baseline(monkeypatch):
    effect = chunk("effect").model_copy(update={"text": "As outer radius increases, flux decreases."})
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_chunk_search", Mock(return_value=[effect]))
    definition = effect_definition(combined=True)
    definition.tool_calls[0]["args"].update(descriptions=["Report flux sensitivity to outer radius."],
        parameter_effects=[{"requirement_index": 1, "baseline_requirement_index": None,
                            "parameter": "outer radius"}])
    terminal = effect_finish()
    terminal.tool_calls[0]["args"]["effect_evidence"][0]["need_id"] = "r1"
    model = FakeToolCallingModel([definition, search(), terminal], define=False)
    result = run_agentic("Report flux sensitivity to outer radius.", client=Mock(), catalogue=Mock(),
        scope=scope(), embed=Mock(return_value=[1.0]), model=model)
    assert result.execution.requirement_correction_attempts == 0
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert len(result.requirements) == 1


def test_effect_finish_cannot_loop_or_increase_round_budget(monkeypatch):
    source = chunk("wrong").model_copy(update={"text": "The inner radius changes; flux is unchanged."})
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_chunk_search", Mock(return_value=[source]))
    invalid = effect_finish(context_id="wrong", parameter="inner radius",
                            outcome="flux is unchanged", kind="reported_no_change")
    model = FakeToolCallingModel([effect_definition(), search(), invalid, invalid], define=False)
    result = run_agentic("Report baseline flux and sensitivity to outer radius.", client=Mock(),
        catalogue=Mock(), scope=scope(), embed=Mock(return_value=[1.0]), model=model,
        budget=AgentBudget(max_rounds=2))
    assert result.execution.stop_reason == StopReason.INSUFFICIENT_EVIDENCE
    assert result.execution.synthesis_policy == "evidence_fallback"
    assert result.execution.rounds == 1 and result.execution.tool_calls == 1
    assert len(result.execution.effect_finish_checks) == 2


def test_missing_parameter_declaration_does_not_silently_allow_sufficient_finish(monkeypatch):
    model = FakeToolCallingModel([call("define_requirements", {
        "descriptions": ["Report flux sensitivity to outer radius."], "initial_searches": [],
        "synthesis_indices": [], "parameter_effects": []}, "second-bad-definition")],
        requirements=("Report flux sensitivity to outer radius.",))
    result = run_agentic("Report flux sensitivity to outer radius.", client=Mock(), catalogue=Mock(),
        scope=scope(), embed=Mock(return_value=[1.0]), model=model)
    assert result.execution.stop_reason == StopReason.PLANNER_FAILURE
    assert result.execution.tool_calls == 0
    assert result.execution.requirement_correction_attempts == 1


def test_native_sdk_parameter_effect_finish_protocol_uses_existing_recovery_round(monkeypatch):
    import json
    import httpx
    from langchain_openai import ChatOpenAI

    responses = [effect_definition(), effect_finish(context_id="wrong", parameter="inner radius",
        outcome="flux is unchanged", kind="reported_no_change"),
        search("recovery", "outer radius flux change", "r2"), effect_finish()]
    responses[0].tool_calls[0]["args"]["initial_searches"] = [
        {"query": "baseline flux", "requirement_indices": [1]},
        {"query": "outer radius dependence", "requirement_indices": [2]}]
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        message = responses[len(requests) - 1]
        calls = [{"id": row["id"], "type": "function", "function": {
            "name": row["name"], "arguments": json.dumps(row["args"])}} for row in message.tool_calls]
        return httpx.Response(200, json={"id": f"chat-{len(requests)}", "object": "chat.completion",
            "created": 0, "model": "gpt-5-mini", "choices": [{"index": 0,
                "finish_reason": "tool_calls", "message": {"role": "assistant", "content": None,
                                                            "tool_calls": calls}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}})

    def lookup(*args, **kwargs):
        return [chunk("effect").model_copy(update={"text": "With outer radius increased, flux decreases."})
                if kwargs["query"] == "outer radius flux change" else
                chunk("wrong").model_copy(update={"text": "The inner radius changes; flux is unchanged."})]

    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_chunk_search", lookup)
    with httpx.Client(transport=httpx.MockTransport(handle)) as http_client:
        model = ChatOpenAI(model="gpt-5-mini", api_key="offline", max_retries=0,
                           max_completion_tokens=2000, http_client=http_client)
        result = run_agentic("Report baseline flux and sensitivity to outer radius.", client=Mock(),
            catalogue=Mock(), scope=scope(), embed=Mock(return_value=[1.0]), model=model,
            budget=AgentBudget(max_rounds=2))
    assert len(requests) == 4
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert result.execution.rounds == 2 and result.execution.tool_calls == 3
    first_schema = requests[0]["tools"][0]["function"]["parameters"]
    assert "parameter_effects" in first_schema["properties"]
    finish_schema = next(row["function"]["parameters"] for row in requests[1]["tools"]
                         if row["function"]["name"] == "finish_with_evidence")
    assert "effect_evidence" in finish_schema["properties"]
    feedback = requests[2]["messages"][-1]
    assert feedback["role"] == "tool" and feedback["tool_call_id"] == responses[1].tool_calls[0]["id"]
    assert json.loads(feedback["content"])["error"] == "effect_evidence_incomplete"


@pytest.mark.parametrize("bad_plan,expected_code", [
    ("null_baseline", "baseline_required"),
    ("query_collision", "baseline_effect_same_query"),
    ("nonliteral_parameter", "parameter_not_in_question"),
    ("valid", None),
])
def test_native_definition_feedback_and_normalized_baseline_effect_searches(monkeypatch, bad_plan, expected_code):
    import json
    import httpx
    from langchain_openai import ChatOpenAI

    title = "A Study of Flux Response to Disk Parameters"
    build_id = "12345678-abcd-1234-abcd-123456789abc"
    boundary = RetrievalScope("papers", (build_id,), builds=(ScopedBuild(build_id, "paper-1"),))
    resolved = SimpleNamespace(title=title, build_id=build_id, paper_id="paper-1", source="uploads")
    monkeypatch.setattr("src.api.rag.modes.agentic.executor.resolve_quoted_papers", lambda *_: [resolved])
    corrected = effect_definition().tool_calls[0]["args"]
    corrected["initial_searches"] = [
        {"query": f'measured flux in "{title}"', "requirement_indices": [1]},
        {"query": f"flux outer radius dependence {build_id}", "requirement_indices": [2],
         "build_ids": [build_id]},
    ]
    invalid = json.loads(json.dumps(corrected))
    if bad_plan == "null_baseline":
        invalid["parameter_effects"][0]["baseline_requirement_index"] = None
    elif bad_plan == "query_collision":
        # Seemingly different inputs collapse to one lookup after identity cleanup.
        invalid["initial_searches"][1]["query"] = f"measured flux {build_id}"
    elif bad_plan == "nonliteral_parameter":
        invalid["parameter_effects"][0]["parameter"] = "radius of the outer disk"
    effect = chunk("effect").model_copy(update={
        "build_id": build_id, "title": title,
        "text": "The measured flux is high. As outer radius increases, flux decreases."})
    backend = Mock(return_value=[effect])
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_chunk_search", backend)
    requests = []

    def handle(request):
        body = json.loads(request.content)
        requests.append(body)
        index = len(requests)
        definition_calls = 2 if expected_code else 1
        if expected_code and index == 2:
            feedback = body["messages"][-1]
            assert feedback["role"] == "tool" and feedback["tool_call_id"] == "call-1"
            issue = json.loads(feedback["content"])["issues"][0]
            assert issue["code"] == expected_code
            assert issue["field"].startswith("parameter_effects[0].")
            assert issue["message"]  # Exactly this application-owned guidance is persisted.
        message = (call("define_requirements", invalid if index == 1 else corrected, f"call-{index}")
                   if index <= definition_calls else effect_finish(call_id=f"call-{index}"))
        tool_calls = [{"id": row["id"], "type": "function", "function": {
            "name": row["name"], "arguments": json.dumps(row["args"])}}
            for row in message.tool_calls]
        return httpx.Response(200, json={"id": f"chat-{index}", "object": "chat.completion",
            "created": 0, "model": "gpt-5-mini", "choices": [{"index": 0,
                "finish_reason": "tool_calls", "message": {"role": "assistant", "content": None,
                                                            "tool_calls": tool_calls}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        model = ChatOpenAI(model="gpt-5-mini", api_key="offline", max_retries=0,
                           max_completion_tokens=2000, http_client=client)
        result = run_agentic(f'Report measured flux and sensitivity to outer radius in "{title}".',
            client=Mock(), catalogue=Mock(), scope=boundary, embed=Mock(return_value=[1.0]),
            model=model, budget=AgentBudget(max_rounds=1))
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert result.execution.requirement_correction_attempts == int(bool(expected_code))
    assert len(requests) == (3 if expected_code else 2)
    assert result.execution.rounds == 1 and result.execution.tool_calls == 2
    assert [row.query for row in result.execution.initial_searches] == [
        "measured flux", "flux outer radius dependence"]
    assert [row.build_ids for row in result.execution.initial_searches] == [[build_id], [build_id]]
    assert backend.call_count == 2  # Rejected plan never executed.
    if expected_code:
        issue = result.execution.requirement_validation_failures[0].issues[0]
        feedback_issue = json.loads(requests[1]["messages"][-1]["content"])["issues"][0]
        assert issue.model_dump() == feedback_issue
    else:
        assert result.execution.requirement_validation_failures == []


def test_normalized_effect_only_search_keeps_null_baseline_and_one_lookup(monkeypatch):
    build_id = "12345678-abcd-1234-abcd-123456789abc"
    effect = chunk("effect").model_copy(update={
        "build_id": build_id, "text": "As outer radius increases, flux decreases."})
    boundary = RetrievalScope("papers", (build_id,), builds=(ScopedBuild(build_id, "paper-1"),))
    backend = Mock(return_value=[effect])
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_chunk_search", backend)
    terminal = effect_finish()
    terminal.tool_calls[0]["args"]["effect_evidence"][0]["need_id"] = "r1"
    model = FakeToolCallingModel([terminal], requirements=["Report flux sensitivity to outer radius."],
        parameter_effects=[{"requirement_index": 1, "parameter": "outer radius",
                            "baseline_requirement_index": None}],
        initial_searches=[{"query": f"flux outer radius dependence {build_id}",
                           "build_ids": [build_id], "requirement_indices": [1]}])
    result = run_agentic("Report flux sensitivity to outer radius.", client=Mock(), catalogue=Mock(),
        scope=boundary, embed=Mock(return_value=[1.0]), model=model)
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert result.execution.requirement_correction_attempts == 0
    assert len(result.requirements) == result.execution.tool_calls == 1
    assert result.execution.parameter_effects[0].baseline_requirement_index is None
    assert result.execution.actions[0].query == "flux outer radius dependence"


def test_normalized_cross_paper_effect_plan_preserves_synthesis_and_duplicate_merging(monkeypatch):
    titles = {"build-1": "A Study of Flux Response to Disk Parameters",
              "build-2": "Numerical Analysis of Stellar Cluster Formation"}
    boundary = RetrievalScope("papers", tuple(titles), builds=(
        ScopedBuild("build-1", "paper-1"), ScopedBuild("build-2", "paper-2")))
    monkeypatch.setattr("src.api.rag.modes.agentic.executor.resolve_quoted_papers", lambda *_: [
        SimpleNamespace(title=title, build_id=build, paper_id=f"paper-{index}", source="uploads")
        for index, (build, title) in enumerate(titles.items(), start=1)])
    effect = chunk("effect").model_copy(update={
        "text": "With outer radius increased, flux decreases.", "title": titles["build-1"]})
    other = chunk("capabilities").model_copy(update={
        "build_id": "build-2", "paper_id": "paper-2", "title": titles["build-2"]})

    def lookup(_client, action_scope, **kwargs):
        return [effect if action_scope.build_ids == ("build-1",) else other]

    backend = Mock(side_effect=lookup)
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_chunk_search", backend)
    baseline_query = f'measured flux in "{titles["build-1"]}"'
    effect_query = f'flux outer radius dependence in "{titles["build-1"]}"'
    initial = [{"query": baseline_query, "requirement_indices": [1]},
               {"query": effect_query, "requirement_indices": [2]},
               {"query": effect_query, "requirement_indices": [2]},
               {"query": f'analysis capabilities in "{titles["build-2"]}"',
                "requirement_indices": [3]}]
    terminal = effect_finish()
    terminal.tool_calls[0]["args"]["question_scope"] = "cross_paper"
    model = FakeToolCallingModel([terminal], requirements=[
        "Report measured flux.", "Report sensitivity to outer radius.",
        "Describe reported analysis capabilities.", "Propose a supported cross-paper test."],
        initial_searches=initial, synthesis_indices=[1, 2, 4],
        parameter_effects=[{"requirement_index": 2, "baseline_requirement_index": 1,
                            "parameter": "outer radius"}])
    result = run_agentic(f'From "{titles["build-1"]}", report measured flux and sensitivity '
        f'to outer radius. Use the analysis capabilities in "{titles["build-2"]}" '
        "to propose a test.", client=Mock(), catalogue=Mock(), scope=boundary,
        embed=Mock(return_value=[1.0]), model=model)
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert result.execution.requirement_correction_attempts == 0
    assert [row.kind for row in result.requirements] == ["fact", "fact", "fact", "synthesis"]
    assert [row.query for row in result.execution.initial_searches] == [
        "measured flux", "flux outer radius dependence", "analysis capabilities"]
    assert result.execution.tool_calls == backend.call_count == 3
    assert result.execution.rounds == 1
    assert result.execution.covered_required_paper_count == 2


def test_second_invalid_effect_plan_keeps_specific_diagnostics_and_stops(monkeypatch, caplog):
    import json
    invalid = effect_definition()
    invalid.tool_calls[0]["args"]["parameter_effects"][0]["baseline_requirement_index"] = None
    backend = Mock()
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_chunk_search", backend)
    model = FakeToolCallingModel([invalid, invalid, finish()], define=False)
    result = run_agentic("Report measured flux and sensitivity to outer radius.", client=Mock(),
        catalogue=Mock(), scope=scope(), embed=Mock(return_value=[1.0]), model=model)
    assert result.execution.stop_reason == StopReason.PLANNER_FAILURE
    assert result.execution.synthesis_policy == "hard_stop"
    assert result.execution.requirement_correction_attempts == 1
    assert [failure.attempt for failure in result.execution.requirement_validation_failures] == [1, 2]
    assert all(failure.issues[0].code == "baseline_required"
               for failure in result.execution.requirement_validation_failures)
    assert "baseline_required" in result.execution.plan_summary and "baseline_required" in caplog.text
    assert "instead of null" in json.loads(model.seen_messages[1][-1].content)["issues"][0]["message"]
    assert result.execution.tool_calls == result.execution.rounds == result.execution.evidence_count == 0
    assert result.execution.planner_tokens == 30 and len(model.responses) == 1
    backend.assert_not_called()


def run(model, monkeypatch, *, chunks=None, error=None, budget=None):
    if error:
        monkeypatch.setattr(
            "src.api.rag.modes.agentic.tools.scoped_chunk_search",
            Mock(side_effect=error),
        )
    else:
        monkeypatch.setattr(
            "src.api.rag.modes.agentic.tools.scoped_chunk_search",
            Mock(return_value=[chunk()] if chunks is None else chunks),
        )
    return run_agentic(
        "What mass is reported?", client=Mock(), catalogue=Mock(), scope=scope(),
        embed=Mock(return_value=[1.0]), model=model, budget=budget or AgentBudget(),
    )


def test_tool_call_then_terminal_call_synthesizes(monkeypatch):
    model = FakeToolCallingModel([search(), finish()])

    result = run(model, monkeypatch)

    assert result.should_synthesize is True
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert result.execution.synthesis_policy == "model_finish"
    assert result.execution.rounds == 1
    assert result.execution.tool_calls == 1
    assert result.execution.evidence_count == 1
    assert result.execution.planner_tokens == 45
    assert model.bind_options[0] == {"tool_choice": "define_requirements", "parallel_tool_calls": False}
    assert result.execution.actions[0].need_id == "r1"
    assert result.execution.actions[0].query == "cluster mass"
    assert result.evidence_by_requirement == {"r1": ("point-1",)}
    assert result.execution.required_evidence_need_count == 1
    assert result.execution.covered_evidence_need_count == 1
    assert {tool.name for tool in model.bound_tools} == {
        "search_papers", "search_chunks", "get_section", "get_neighbors",
        "finish_with_evidence", "abstain",
    }


def test_repeated_tool_call_stops_without_second_execution(monkeypatch):
    tool = Mock(return_value=[chunk()])
    monkeypatch.setattr(
        "src.api.rag.modes.agentic.tools.scoped_chunk_search", tool,
    )
    result = run_agentic(
        "Question", client=Mock(), catalogue=Mock(), scope=scope(),
        embed=Mock(return_value=[1.0]),
        model=FakeToolCallingModel([search(), search("retry")]),
        budget=AgentBudget(),
    )

    assert result.should_synthesize is True
    assert result.execution.stop_reason == StopReason.REPEATED_ACTION
    assert result.execution.synthesis_policy == "evidence_fallback"
    assert result.execution.rounds == 1
    assert result.execution.tool_calls == 1
    assert tool.call_count == 1


def test_duplicate_chunk_is_mapped_to_each_atomic_evidence_need(monkeypatch):
    parallel = AIMessage(
        content="",
        tool_calls=[
            search("mass", "cluster mass", "r1").tool_calls[0],
            search("radius", "cluster radius", "r2").tool_calls[0],
        ],
        usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    )

    result = run(FakeToolCallingModel([parallel, finish()],
                 requirements=("Report the mass.", "Report the radius.")), monkeypatch)

    assert result.should_synthesize is True
    assert result.execution.evidence_count == 1
    assert result.evidence_by_requirement == {
        "r1": ("point-1",),
        "r2": ("point-1",),
    }


def test_search_labels_do_not_gate_final_answer_coverage(monkeypatch):
    search_tool = Mock(side_effect=[[chunk()], []])
    monkeypatch.setattr(
        "src.api.rag.modes.agentic.tools.scoped_chunk_search", search_tool,
    )
    model = FakeToolCallingModel(
        [search(), finish()], requirements=("Report the mass.", "Report the radius."))

    result = run_agentic(
        "Report the mass and radius.", client=Mock(), catalogue=Mock(), scope=scope(),
        embed=Mock(return_value=[1.0]), model=model, budget=AgentBudget(),
    )

    assert result.should_synthesize is True
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert result.execution.missing_evidence_need_ids == ["r2"]
    assert result.execution.covered_evidence_need_count == 1


def test_tool_failure_stops_safely(monkeypatch):
    result = run(
        FakeToolCallingModel([search()]), monkeypatch,
        error=RuntimeError("offline"),
    )

    assert result.execution.stop_reason == StopReason.TOOL_FAILURE
    assert result.execution.actions[0].status == "error"
    assert result.should_synthesize is False


def test_explicit_abstention_does_not_synthesize(monkeypatch):
    abstain = call("abstain", {
        "summary": "No indexed evidence.", "question_scope": "direct",
    }, "call_abstain")

    result = run(FakeToolCallingModel([abstain]), monkeypatch, chunks=[])

    assert result.execution.stop_reason == StopReason.INSUFFICIENT_EVIDENCE
    assert result.should_synthesize is False
    assert result.execution.rounds == 0


def test_explicit_abstention_after_retrieval_uses_grounded_fallback(monkeypatch):
    abstain = call("abstain", {
        "summary": "The planner considers the evidence incomplete.",
        "question_scope": "direct",
    }, "call_abstain")

    result = run(FakeToolCallingModel([search(), abstain]), monkeypatch)

    assert result.execution.stop_reason == StopReason.INSUFFICIENT_EVIDENCE
    assert result.execution.synthesis_policy == "evidence_fallback"
    assert result.should_synthesize is True
    assert result.execution.evidence_count == 1


def test_plain_text_model_response_fails_closed(monkeypatch):
    result = run(
        FakeToolCallingModel([AIMessage(content="Here is an unsupported answer")]),
        monkeypatch,
    )

    assert result.execution.stop_reason == StopReason.PLANNER_FAILURE
    assert result.execution.tool_calls == 0


def test_invalid_terminal_scope_fails_closed(monkeypatch):
    invalid = call("finish_with_evidence", {
        "summary": "Unsupported scope.", "question_scope": "everything",
    }, "call_invalid")

    result = run(FakeToolCallingModel([invalid]), monkeypatch)

    assert result.execution.stop_reason == StopReason.PLANNER_FAILURE
    assert result.should_synthesize is False


def test_round_budget_allows_terminal_but_rejects_more_retrieval(monkeypatch):
    result = run(
        FakeToolCallingModel([search(), search("call_2", "cluster radius")]),
        monkeypatch, budget=AgentBudget(max_rounds=1),
    )

    assert result.execution.stop_reason == StopReason.MAX_ROUNDS
    assert result.execution.synthesis_policy == "evidence_fallback"
    assert result.should_synthesize is True
    assert result.execution.rounds == 1
    assert result.execution.tool_calls == 1


def test_named_cross_paper_question_cannot_finish_with_missing_paper(monkeypatch):
    cross_scope = RetrievalScope("papers", ("build-1", "build-2"), builds=(
        ScopedBuild("build-1", "paper-1"), ScopedBuild("build-2", "paper-2"),
    ))
    rows = [
        {"id": "build-1", "paper_id": "paper-1", "source": "arxiv",
         "source_id": "one", "active_build": "build-1", "deleted": 0,
         "collection": "papers", "version": 1, "status": "ready",
         "metadata": {"title": "First named scientific paper"}},
        {"id": "build-2", "paper_id": "paper-2", "source": "arxiv",
         "source_id": "two", "active_build": "build-2", "deleted": 0,
         "collection": "papers", "version": 1, "status": "ready",
         "metadata": {"title": "Second named scientific paper"}},
    ]
    monkeypatch.setattr(
        "src.api.rag.modes.agentic.tools.scoped_chunk_search",
        Mock(return_value=[chunk()]),
    )
    first_only = call("search_chunks", {
        "need_id": "r1",
        "query": "first result", "retrieval_mode": "hybrid",
        "build_ids": ["build-1"], "paper_ids": ["paper-1"], "limit": 5,
    }, "first")

    result = run_agentic(
        'Compare "First named scientific paper" and "Second named scientific paper".',
        client=Mock(), catalogue=SimpleNamespace(all_builds=lambda: rows),
        scope=cross_scope, embed=Mock(return_value=[1.0]),
        model=FakeToolCallingModel([first_only, finish()]), budget=AgentBudget(),
    )

    assert result.should_synthesize is True
    assert result.execution.stop_reason == StopReason.INSUFFICIENT_EVIDENCE
    assert result.execution.required_paper_count == 2
    assert result.execution.covered_required_paper_count == 1
    assert result.execution.missing_required_build_ids == ["build-2"]


def test_retrieval_without_atomic_need_id_fails_before_tool_execution(monkeypatch):
    tool = Mock(return_value=[chunk()])
    monkeypatch.setattr(
        "src.api.rag.modes.agentic.tools.scoped_chunk_search", tool,
    )
    missing_need = call("search_chunks", {
        "query": "cluster mass", "retrieval_mode": "hybrid",
        "build_ids": [], "paper_ids": [], "limit": 5,
    }, "missing_need")

    result = run_agentic(
        "Question", client=Mock(), catalogue=Mock(), scope=scope(),
        embed=Mock(return_value=[1.0]),
        model=FakeToolCallingModel([missing_need]), budget=AgentBudget(),
    )

    assert result.execution.stop_reason == StopReason.PLANNER_FAILURE
    assert result.execution.tool_calls == 0
    assert tool.call_count == 0


def test_scope_policy_rejects_ids_outside_corpus():
    corpus = scope()
    for builds, papers in [(["outside"], []), ([], ["outside-paper"])]:
        try:
            narrow_scope(corpus, builds, papers)
        except ValueError as exc:
            assert "outside the approved corpus" in str(exc)
        else:
            raise AssertionError("Out-of-scope filter was accepted")

    narrowed = narrow_scope(corpus, ["build-1"], ["paper-1"])
    assert narrowed.build_ids == ("build-1",)
    assert narrowed.paper_ids == ("paper-1",)


def test_action_fingerprint_ignores_observability_need_id():
    first = action_fingerprint("search_chunks", {
        "need_id": "oiii_width", "query": "broad O III FWHM", "build_ids": ["build-1"],
    })
    renamed = action_fingerprint("search_chunks", {
        "need_id": "renamed", "query": "broad O III FWHM", "build_ids": ["build-1"],
    })

    assert first == renamed


def test_compound_named_paper_requirements_use_qdrant_build_filter(monkeypatch):
    title = "A Detailed Scientific Paper About Cluster Masses"
    required = SimpleNamespace(build_id="build-1", paper_id="paper-1", title=title)
    monkeypatch.setattr(
        "src.api.rag.modes.agentic.executor.resolve_quoted_papers",
        Mock(return_value=[required]),
    )
    tool = Mock(return_value=[chunk()])
    monkeypatch.setattr(
        "src.api.rag.modes.agentic.tools.scoped_chunk_search", tool,
    )
    corpus = RetrievalScope("papers", ("build-1", "build-2"), builds=(
        ScopedBuild("build-1", "paper-1"), ScopedBuild("build-2", "paper-2"),
    ))
    descriptions = (
        f"Report cluster mass as reported in {title} "
        "(paper_id=paper-1; required_build_id=build-1).",
        f"Report cluster radius as reported in {title} "
        "(paper_id=paper-1; required_build_id=build-1).",
    )
    result = run_agentic(
        f'Compare mass and radius in "{title}".',
        client=Mock(), catalogue=Mock(), scope=corpus,
        embed=Mock(return_value=[1.0]),
        model=FakeToolCallingModel([finish()], requirements=descriptions, initial_searches=[
            {"query": f"cluster mass in {title} (required_build_id=build-1)",
             "requirement_indices": [1], "build_ids": ["build-1"]},
            {"query": f"cluster radius in {title} (paper_id=paper-1)",
             "requirement_indices": [2], "build_ids": ["build-1"]},
        ]),
        budget=AgentBudget(),
    )
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert result.execution.tool_calls == 2
    assert tool.call_count == 2
    for call_args in tool.call_args_list:
        assert call_args.args[1].build_ids == ("build-1",)
        assert title not in call_args.kwargs["query"]
        assert "required_build_id" not in call_args.kwargs["query"]
        assert "paper_id" not in call_args.kwargs["query"]
    assert "cluster mass" in result.execution.actions[0].query
    assert "cluster radius" in result.execution.actions[1].query


def test_retrieval_before_requirement_definition_is_rejected(monkeypatch):
    result = run(FakeToolCallingModel([search()], define=False), monkeypatch)
    assert result.execution.stop_reason == StopReason.PLANNER_FAILURE
    assert result.execution.tool_calls == 0
    assert result.requirements == []


def test_initial_queries_are_distinct_from_answer_requirements(monkeypatch):
    result = run(FakeToolCallingModel(
        [finish()], requirements=("Report the mass.", "Report the age."), initial_searches=[
            {"query": "cluster mass estimates", "requirement_indices": [1]},
            {"query": "cluster age fits", "requirement_indices": [2]},
        ]),
        monkeypatch)
    assert [row.id for row in result.requirements] == ["r1", "r2"]
    assert [row.need_id for row in result.execution.actions[:2]] == ["r1", "r2"]
    assert [row.query for row in result.execution.actions[:2]] == [
        "cluster mass estimates", "cluster age fits",
    ]
    assert result.execution.missing_evidence_need_ids == []
    assert result.should_synthesize is True
    assert result.execution.synthesis_policy == "model_finish"


def test_initial_plan_stops_safely_when_tool_budget_is_exhausted(monkeypatch):
    model = FakeToolCallingModel(
        [finish()], requirements=("Report the mass.", "Report the age."), initial_searches=[
            {"query": "cluster mass", "requirement_indices": [1]},
            {"query": "cluster age", "requirement_indices": [2]},
        ])
    result = run(model,
        monkeypatch, budget=AgentBudget(max_tool_calls=1))

    assert result.execution.stop_reason == StopReason.TOOL_CALL_BUDGET
    assert result.execution.tool_calls == 1
    assert [row.need_id for row in result.execution.actions] == ["r1"]
    assert result.execution.missing_evidence_need_ids == ["r2"]
    assert result.should_synthesize is True
    assert len(model.responses) == 1  # No paid planner call after the budget stop.


def test_search_cannot_create_new_answer_requirement(monkeypatch):
    result = run(FakeToolCallingModel([
        search(), search("invented", "age", need_id="new_requirement"),
    ]), monkeypatch)
    assert result.execution.tool_calls == 1
    assert result.execution.stop_reason == StopReason.PLANNER_FAILURE
    assert [row.id for row in result.requirements] == ["r1"]
    assert result.should_synthesize is True


def test_requirement_definition_cannot_be_replaced_after_retrieval(monkeypatch):
    redefine = call("define_requirements", {"descriptions": ["Different request"]}, "redefine")
    result = run(FakeToolCallingModel([search(), redefine]), monkeypatch)
    assert result.execution.stop_reason == StopReason.PLANNER_FAILURE
    assert result.requirements[0].description == "Report the mass."
    assert result.should_synthesize is True


def test_duplicate_requirement_definitions_rejected_before_retrieval(monkeypatch):
    result = run(FakeToolCallingModel(
        [search()], requirements=("Report the mass.", " REPORT THE MASS. ")), monkeypatch)
    assert result.execution.stop_reason == StopReason.PLANNER_FAILURE
    assert result.execution.tool_calls == 0


def test_reformulation_reuses_requirement_without_adding_mandatory_citations(monkeypatch):
    result = run(FakeToolCallingModel([
        search(), search("reformulate", "stellar cluster mass"), finish(),
    ]), monkeypatch)
    assert result.execution.tool_calls == 2
    assert len(result.requirements) == 1
    assert result.execution.required_evidence_need_count == 1
    assert result.should_synthesize is True


def test_expanded_text_reaches_planner_even_when_chunk_was_already_retrieved(monkeypatch):
    import json
    from langchain_core.messages import ToolMessage

    row = chunk().model_copy(update={
        "text": "Introductory background. " * 40 + "The cluster mass is 100 solar masses."})
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_neighbors",
                        Mock(return_value=[row]))
    expand = call("get_neighbors", {
        "need_id": "r1", "build_id": "build-1", "paper_id": "paper-1",
        "chunk_index": 4, "before": 0, "after": 0,
    }, "read_anchor")

    class ReadingModel(FakeToolCallingModel):
        seen = None

        def invoke(self, messages):
            self.seen = list(messages)
            return super().invoke(messages)

    model = ReadingModel([search(), expand, finish()])
    result = run(model, monkeypatch, chunks=[row])
    messages = [message for message in model.seen if isinstance(message, ToolMessage)]
    preview = json.loads(next(message.content for message in messages
                              if message.name == "search_chunks"))
    expanded = json.loads(next(message.content for message in messages
                               if message.name == "get_neighbors"))
    assert "100 solar masses" not in preview["evidence"][0]["text"]
    assert "100 solar masses" in expanded["evidence"][0]["text"]
    assert expanded["evidence"][0]["text_truncated"] is False
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert result.execution.rounds == 2
    assert result.execution.evidence_count == 1
    assert result.evidence[0].text == row.text

def test_planner_reserves_next_prompt_and_output_before_call(monkeypatch):
    class CountingModel(FakeToolCallingModel):
        max_tokens = 20

        def get_num_tokens_from_messages(self, messages):
            return 220 if len(self.responses) == 1 else 30

        def get_num_tokens(self, text):
            return 10

    model = CountingModel([search(), finish()])
    result = run(model, monkeypatch, budget=AgentBudget(max_planner_tokens=512))

    assert result.execution.stop_reason == StopReason.TOKEN_BUDGET
    assert result.execution.planner_tokens == 30
    assert result.execution.next_call_estimated_tokens == 506
    assert result.execution.evidence_count == 1
    assert result.execution.synthesis_policy == 'evidence_fallback'
    assert len(model.responses) == 1


def test_catalogue_confirmed_titles_and_references_become_filters_not_search_terms():
    titles = {"build-1": "Scientific Results. V. Cluster Masses", "build-2": "Another Paper About Stars"}
    query, builds = scoped_requirement_query(
        "Scientific Results V Cluster Masses mass supply arXiv 2609.00001v2", [], titles,
        explicit_build_ids=True, required_source_ids={"build-1": "2609.00001"})
    assert query == "mass supply"
    assert builds == ["build-1"]
    query, builds = scoped_requirement_query("cluster masses in galaxies", [], titles,
                                             explicit_build_ids=True)
    assert query == "cluster masses in galaxies"
    assert builds == []  # Partial titles/concepts must not narrow the scope.
    query, builds = scoped_requirement_query("Scientific Results. V. Cluster Masses", [], titles,
                                             explicit_build_ids=True)
    assert query == "paper findings"  # Never put a removed title back into a fact query.
    assert builds == ["build-1"]
    query, builds = scoped_requirement_query(
        "mass supply https://arxiv.org/pdf/2609.00001v2.pdf", [], titles,
        explicit_build_ids=True, required_source_ids={"build-1": "2609.00001"})
    assert query == "mass supply"
    assert builds == ["build-1"]


def test_initial_and_recovery_searches_use_explicit_arxiv_filters(monkeypatch):
    title = "An Unquoted Scientific Paper About Cluster Measurements"
    rows = [{"id": "build-1", "paper_id": "paper-1", "source": "arxiv",
             "source_id": "2609.00001", "active_build": "build-1", "deleted": 0,
             "collection": "papers", "version": 2, "status": "ready",
             "metadata": {"title": title}}]
    lookup = Mock(side_effect=[[chunk()], [chunk("sensitivity")]])
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_chunk_search", lookup)
    model = FakeToolCallingModel([
        search("recovery", f"outer radius sensitivity {title} arXiv:2609.00001v2"), finish(),
    ], requirements=("Report the mass supply and its radius sensitivity.",), initial_searches=[
        {"query": f"{title} mass supply arXiv 2609.00001v2", "requirement_indices": [1]},
    ])
    result = run_agentic(
        f"Report the mass supply and its radius sensitivity in {title} (arXiv:2609.00001v2).",
        client=Mock(), catalogue=SimpleNamespace(all_builds=lambda: rows), scope=scope(),
        embed=Mock(return_value=[1.0]), model=model,
        budget=AgentBudget(max_rounds=2, max_tool_calls=2),
    )
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert result.execution.required_paper_count == 1
    assert result.execution.tool_calls == 2
    assert [row.query for row in result.execution.actions] == ["mass supply", "outer radius sensitivity"]
    assert all(args.args[1].build_ids == ("build-1",) for args in lookup.call_args_list)
    assert [row.id for row in result.evidence] == ["point-1", "sensitivity"]


def test_observed_markdown_section_heading_is_used_exactly(monkeypatch):
    heading = "## **2.2 Clustering around Massive Stars**"
    row = chunk().model_copy(update={"section_header": heading})
    lookup = Mock(return_value=[row])
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_section", lookup)
    section_call = call("get_section", {
        "need_id": "r1", "build_id": "build-1", "paper_id": "paper-1",
        "section_header": "2.2 Clustering around Massive Stars",
    }, "section")
    result = run(FakeToolCallingModel([search(), section_call, finish()]), monkeypatch, chunks=[row])
    assert lookup.call_args.kwargs["section_header"] == heading
    assert result.execution.actions[1].query == f"section_header={heading}"
    assert result.execution.stop_reason == StopReason.SUFFICIENT


def test_section_header_recovery_never_guesses_or_crosses_paper_identity():
    row = chunk().model_copy(update={"section_header": "## **Clustering around Massive Stars**"})
    assert observed_section_header("Clustering", [row], build_id="build-1", paper_id="paper-1") == "Clustering"
    assert observed_section_header("Clustering around Massive Stars", [row], build_id="build-2",
                                   paper_id="paper-1") == "Clustering around Massive Stars"
    scientific = chunk().model_copy(update={"section_header": "## **M* populations**"})
    assert observed_section_header("M populations", [scientific], build_id="build-1",
                                   paper_id="paper-1") == "M populations"
    ambiguous = row.model_copy(update={"section_header": "Clustering around Massive Stars"})
    assert observed_section_header("## Clustering around Massive Stars", [row, ambiguous],
                                   build_id="build-1", paper_id="paper-1") == "## Clustering around Massive Stars"


def test_budget_compaction_allows_existing_recovery_round_without_changing_evidence(monkeypatch):
    import json
    from langchain_core.messages import ToolMessage

    row = chunk().model_copy(update={
        "text": "Background without the requested fact. " * 250
        + "The sensitivity is measured by varying the parameter and comparing rates."})
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_neighbors", Mock(return_value=[row]))
    expand = call("get_neighbors", {
        "need_id": "r1", "build_id": "build-1", "paper_id": "paper-1",
        "chunk_index": 4, "before": 0, "after": 0,
    }, "expand")

    class CountingModel(FakeToolCallingModel):
        max_tokens = 20
        seen = None

        def get_num_tokens_from_messages(self, messages):
            large = any(isinstance(message, ToolMessage) and len(message.content) > 8000
                        for message in messages)
            return 220 if large else 30

        def get_num_tokens(self, text):
            return 10

        def invoke(self, messages):
            self.seen = list(messages)
            return super().invoke(messages)

    model = CountingModel([search(), expand, finish()], requirements=("Report the sensitivity.",))
    result = run(model, monkeypatch, chunks=[row], budget=AgentBudget(max_planner_tokens=512))
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert result.execution.planner_context_compactions == 1
    assert result.execution.planner_tokens == 60
    assert result.execution.rounds == 2
    assert result.evidence[0].text == row.text
    expanded = next(message for message in model.seen
                    if isinstance(message, ToolMessage) and message.tool_call_id == "expand")
    payload = json.loads(expanded.content)
    assert payload["planner_context_compacted"] is True
    assert "sensitivity is measured" in payload["evidence"][0]["text"]
    assert payload["evidence"][0]["text_truncated"] is True
    assert len(model.responses) == 0


def test_compaction_token_counter_failure_does_not_bypass_budget(monkeypatch):
    class CountingModel(FakeToolCallingModel):
        max_tokens = 20

        def get_num_tokens_from_messages(self, messages):
            if any("planner_context_compacted" in str(message.content) for message in messages):
                raise NotImplementedError("No compacted count available")
            return 220 if len(self.responses) == 1 else 30

        def get_num_tokens(self, text):
            return 10

    model = CountingModel([search(), finish()])
    result = run(model, monkeypatch, budget=AgentBudget(max_planner_tokens=512))
    assert result.execution.stop_reason == StopReason.TOKEN_BUDGET
    assert result.execution.next_call_estimated_tokens == 506
    assert result.execution.planner_context_compaction_attempts == 1
    assert len(model.responses) == 1


def test_compaction_removes_completed_definition_pair_without_orphaning_tools():
    import json
    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
    from src.api.rag.modes.agentic.contracts import AnswerRequirement, ParameterEffectNeed
    from src.api.rag.modes.agentic.planner_context import compact_planner_messages
    definition = effect_definition()
    definition_id = definition.tool_calls[0]["id"]
    definition_reply = ToolMessage(name="define_requirements", tool_call_id=definition_id,
                                   content="Repeated description " * 500)
    lookup = search()
    payload = {"evidence": [{"id": "x", "build_id": "build-1", "paper_id": "paper-1",
        "title": "Long title " * 100, "page": 4, "chunk_index": 5,
        "section_header": "Results", "text": "Background " * 1000 + "outer radius changes flux",
        "text_chars": 11025, "text_truncated": False}], "papers": []}
    tool_reply = ToolMessage(name="search_chunks", tool_call_id="call_search", content=json.dumps(payload))
    question = HumanMessage(content="Report flux and sensitivity to outer radius.")
    messages = [SystemMessage(content="Fixed rules."), question, definition, definition_reply, lookup, tool_reply]
    frozen = [AnswerRequirement(id="r1", description="Report flux."),
              AnswerRequirement(id="r2", description="Report sensitivity to outer radius.",
                                effect_parameters=["outer radius"])]
    compact = compact_planner_messages(messages, frozen,
        [ParameterEffectNeed(requirement_index=2, baseline_requirement_index=1, parameter="outer radius")])
    assert question in compact
    assert len(str(compact)) < len(str(messages))
    assert all(getattr(message, "tool_call_id", None) != definition_id for message in compact)
    calls = {call["id"] for message in compact if isinstance(message, AIMessage) for call in message.tool_calls}
    assert {message.tool_call_id for message in compact if isinstance(message, ToolMessage)} == calls
    snapshot = next(message for message in compact if "Frozen retrieval navigation" in str(message.content))
    assert '"parameter": "outer radius"' in snapshot.content
    assert '"id": "r2"' in snapshot.content
    assert '"title":' in compact[-1].content  # Paper catalogue retains resolution context once.
    assert json.loads(tool_reply.content) == payload  # Original source view unchanged.


def run_with_backend(monkeypatch, backend, model, *, budget=None, embed=None):
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_chunk_search", backend)
    return run_agentic(
        "Report the requested cluster properties.", client=Mock(), catalogue=Mock(),
        scope=scope(), embed=embed or Mock(return_value=[1.0]), model=model,
        budget=budget or AgentBudget())


def test_initial_searches_actually_overlap(monkeypatch):
    both_started = Barrier(2)

    def backend(*_args, **kwargs):
        both_started.wait(timeout=5)  # Sequential execution fails, regardless of machine speed.
        return [chunk(kwargs["query"])]

    model = FakeToolCallingModel([finish()], requirements=("Report mass.", "Report age."),
                                initial_searches=[
        {"query": "stellar mass estimate", "requirement_indices": [1]},
        {"query": "isochrone age fit", "requirement_indices": [2]},
    ])
    result = run_with_backend(monkeypatch, backend, model)
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert result.execution.rounds == 1
    assert result.execution.tool_calls == 2
    assert result.execution.planner_tokens == 30  # Definition plus finish; no search-plan call.
    assert result.execution.max_parallel_tools == 4
    assert model.bind_options[1]["parallel_tool_calls"] is True
    assert [row.query for row in result.execution.initial_searches] == [
        "stellar mass estimate", "isochrone age fit"]


def test_additional_searches_actually_overlap_after_initial_results(monkeypatch):
    both_started = Barrier(2)

    def backend(*_args, **kwargs):
        if kwargs["query"] != "initial properties":
            both_started.wait(timeout=5)
        return [chunk(kwargs["query"])]

    additional = AIMessage(content="", tool_calls=[
        search("mass_followup", "dynamical mass", "r1").tool_calls[0],
        search("age_followup", "age uncertainties", "r2").tool_calls[0],
    ])

    class Model(FakeToolCallingModel):
        def invoke(self, messages):
            if self.responses and self.responses[0] is additional:
                assert any(getattr(message, "name", None) == "search_chunks"
                           for message in messages)
            return super().invoke(messages)

    result = run_with_backend(monkeypatch, backend, Model(
        [additional, finish()], requirements=("Report mass.", "Report age."),
        initial_searches=[{"query": "initial properties", "requirement_indices": [1, 2]}]))
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert result.execution.rounds == 2
    assert result.execution.tool_calls == 3
    assert [row.query for row in result.execution.actions] == [
        "initial properties", "dynamical mass", "age uncertainties"]


def test_concurrency_cap_is_honored_without_splitting_a_round(monkeypatch):
    lock = Lock()
    two_started = Barrier(2)
    active = peak = 0

    def backend(*_args, **kwargs):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            two_started.wait(timeout=5)
            return [chunk(kwargs["query"])]
        finally:
            with lock:
                active -= 1

    model = FakeToolCallingModel([finish()], initial_searches=[
        {"query": f"property {i}", "requirement_indices": [1]} for i in range(4)])
    result = run_with_backend(monkeypatch, backend, model,
                              budget=AgentBudget(max_parallel_tools=2))
    assert peak == 2
    assert result.execution.rounds == 1
    assert result.execution.tool_calls == 4
    assert result.execution.stop_reason == StopReason.SUFFICIENT


def test_parallel_results_merge_in_plan_order_under_evidence_cap(monkeypatch):
    second_completed = Event()

    def backend(*_args, **kwargs):
        if kwargs["query"] == "first":
            assert second_completed.wait(timeout=5)
        else:
            second_completed.set()
        return [chunk(kwargs["query"])]

    result = run_with_backend(monkeypatch, backend, FakeToolCallingModel(
        [finish()], initial_searches=[
            {"query": "first", "requirement_indices": [1]},
            {"query": "second", "requirement_indices": [1]},
        ]), budget=AgentBudget(max_evidence_chunks=1))
    assert [row.id for row in result.evidence] == ["first"]
    assert result.execution.actions[1].result_count == 1
    assert result.execution.actions[1].evidence_ids == []


def test_parallel_failure_preserves_successful_sibling(monkeypatch):
    both_started = Barrier(2)

    def backend(*_args, **kwargs):
        both_started.wait(timeout=5)
        if kwargs["query"] == "broken":
            raise RuntimeError("offline")
        return [chunk()]

    result = run_with_backend(monkeypatch, backend, FakeToolCallingModel(
        [finish()], initial_searches=[
            {"query": "broken", "requirement_indices": [1]},
            {"query": "working", "requirement_indices": [1]},
        ]))
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert [row.status for row in result.execution.actions] == ["error", "success"]
    assert result.should_synthesize
    assert result.execution.evidence_count == 1


def test_one_search_can_support_multiple_facts_and_a_synthesis_task(monkeypatch):
    result = run(FakeToolCallingModel(
        [finish()], requirements=("Report mass.", "Report age.", "Compare both estimates."),
        synthesis_indices=[3], initial_searches=[
            {"query": "cluster mass age estimates", "requirement_indices": [1, 2]},
        ]), monkeypatch)
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert result.execution.tool_calls == 1
    assert result.execution.required_evidence_need_count == 2
    assert result.execution.covered_evidence_need_count == 2
    assert result.execution.actions[0].need_ids == ["r1", "r2"]
    assert result.evidence_by_requirement == {"r1": ("point-1",), "r2": ("point-1",)}
    assert result.requirements[2].kind == "synthesis"
    assert len(result.requirements) == 3  # Still passed to final semantic answer coverage.


def test_searched_measurements_cannot_be_hidden_as_synthesis_requirements(monkeypatch):
    result = run(FakeToolCallingModel(
        [finish()], requirements=("Report mass.", "Report distance sensitivity.", "Compare implications."),
        synthesis_indices=[1, 2, 3], initial_searches=[
            {"query": "measured cluster mass", "requirement_indices": [1]},
            {"query": "mass dependence on distance scaling", "requirement_indices": [2]},
        ]), monkeypatch)
    assert [row.kind for row in result.requirements] == ["fact", "fact", "synthesis"]
    assert result.execution.required_evidence_need_count == 2
    assert [row.query for row in result.execution.actions] == [
        "measured cluster mass", "mass dependence on distance scaling"]


def test_baseline_and_parameter_effect_have_distinct_parallel_targets_and_native_guidance(monkeypatch):
    from src.api.rag.modes.agentic.graph import SYSTEM_PROMPT
    from src.api.rag.modes.agentic.tools import define_requirements
    barrier = Barrier(2)

    def backend(*args, **kwargs):
        barrier.wait(timeout=5)
        return [chunk("baseline" if kwargs["query"] == "measured temperature" else "effect")]

    result = run_with_backend(monkeypatch, backend, FakeToolCallingModel([finish()],
        requirements=("Report the measured temperature.", "Report temperature sensitivity to pressure."),
        initial_searches=[{"query": "measured temperature", "requirement_indices": [1]},
                          {"query": "temperature pressure dependence change", "requirement_indices": [2]}]))
    assert result.execution.rounds == 1
    assert result.execution.tool_calls == 2
    assert [row.need_id for row in result.execution.actions] == ["r1", "r2"]
    assert result.evidence_by_requirement == {"r1": ("baseline",), "r2": ("effect",)}
    assert "TWO distinct factual requirements and TWO focused" in SYSTEM_PROMPT
    assert "Recover ONLY the missing factual target" in SYSTEM_PROMPT
    description = define_requirements.args_schema.model_json_schema()["properties"]["descriptions"]["description"]
    assert "separate focused initial queries" in description


def test_bare_resolved_build_id_is_removed_from_query_but_filter_remains():
    build_id = "12345678-abcd-1234-abcd-123456789abc"
    query, builds = scoped_requirement_query(
        f"mass sensitivity to distance {build_id}", [build_id], {}, explicit_build_ids=True)
    assert query == "mass sensitivity to distance"
    assert builds == [build_id]
    # Unknown identifiers never become filters or get silently interpreted as one.
    query, builds = scoped_requirement_query(f"mass {build_id}", [], {})
    assert query == f"mass {build_id}"
    assert builds == []


@pytest.mark.parametrize("prefix", ["12345678", "12345678-abcd", "12345678-abcd-1234"])
def test_short_build_prefix_is_removed_only_with_a_confirmed_filter(prefix):
    build_id = "12345678-abcd-1234-abcd-123456789abc"
    query, builds = scoped_requirement_query(
        f"measured mass distance dependence {prefix}", [build_id], {}, explicit_build_ids=True)
    assert query == "measured mass distance dependence"
    assert builds == [build_id]
    query, builds = scoped_requirement_query(f"mass {prefix}", [], {})
    assert query == f"mass {prefix}"
    assert builds == []


def test_unknown_short_id_and_short_scientific_numbers_are_not_removed():
    build_id = "12345678-abcd-1234-abcd-123456789abc"
    query, builds = scoped_requirement_query(
        "mass 87654321 distance 1234", [build_id], {}, explicit_build_ids=True)
    assert query == "mass 87654321 distance 1234"
    assert builds == [build_id]


@pytest.mark.parametrize("plan", [
    {"query": "mass", "requirement_indices": [2]},
    {"query": "mass", "requirement_indices": [1, 1]},
    {"query": "mass", "requirement_indices": []},
    {"query": "mass", "requirement_indices": [0]},
    {"query": "mass", "requirement_indices": [1], "build_ids": ["outside"]},
    {"query": "mass", "requirement_indices": [1], "paper_ids": ["outside"]},
    {"query": "mass", "requirement_indices": [1], "limit": 21},
])
def test_invalid_initial_plan_does_not_embed_or_search(monkeypatch, plan):
    embed = Mock(return_value=[1.0])
    backend = Mock(return_value=[chunk()])
    result = run_with_backend(monkeypatch, backend,
                              FakeToolCallingModel([finish()], initial_searches=[plan]),
                              embed=embed)
    assert result.execution.stop_reason == StopReason.PLANNER_FAILURE
    assert result.execution.tool_calls == 0
    embed.assert_not_called()
    backend.assert_not_called()


def test_duplicate_initial_queries_merge_requirement_associations(monkeypatch):
    backend = Mock(return_value=[chunk()])
    result = run_with_backend(monkeypatch, backend, FakeToolCallingModel(
        [finish()], requirements=("Mass.", "Age."), initial_searches=[
            {"query": "same search", "requirement_indices": [1]},
            {"query": "same search", "requirement_indices": [2]},
        ]))
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    backend.assert_called_once()
    assert result.execution.actions[0].need_ids == ["r1", "r2"]
    assert result.execution.covered_evidence_need_count == 2


@pytest.mark.parametrize("limit", [0, 9])
def test_invalid_concurrency_budget_is_rejected(limit):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AgentBudget(max_parallel_tools=limit)


@pytest.mark.parametrize("bad_args,field", [
    ({"descriptions": ["Report mass.", "initial_searches"], "initial_searches": []},
     "descriptions[1]"),
    ({"initial_searches": []}, "descriptions"),
    ({"descriptions": ["Report mass."]}, "initial_searches"),
    ({"descriptions": ["Report mass."], "initial_searches": [
        {"requirement_indices": [1]}]}, "initial_searches[0].query"),
    ({"descriptions": ["Report mass."], "initial_searches": [
        {"query": "mass"}]}, "initial_searches[0].requirement_indices"),
    ({"descriptions": ["Report mass."], "initial_searches": [
        {"query": "mass", "requirement_indices": [0]}]},
     "initial_searches[0].requirement_indices[0]"),
])
def test_invalid_definition_gets_one_native_correction(monkeypatch, bad_args, field):
    import json
    from langchain_core.messages import ToolMessage

    corrected = call("define_requirements", {
        "descriptions": ["Report mass."], "initial_searches": [
            {"query": "mass estimate", "requirement_indices": [1]}]}, "fixed")
    model = FakeToolCallingModel([
        call("define_requirements", bad_args, "invalid"), corrected, finish()], define=False)
    result = run(model, monkeypatch, budget=AgentBudget(max_rounds=1))

    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert result.execution.requirement_correction_attempts == 1
    assert len(result.execution.requirement_validation_failures) == 1
    assert result.execution.requirement_validation_failures[0].issues[0].field == field
    assert result.execution.rounds == result.execution.tool_calls == 1
    assert result.execution.planner_tokens == 45
    assert len(model.seen_messages) == 3
    reply = model.seen_messages[1][-1]
    assert isinstance(reply, ToolMessage)
    assert reply.tool_call_id == "invalid"
    assert reply.status == "error"
    assert json.loads(reply.content)["issues"][0]["field"] == field
    assert result.execution.actions[0].query == "mass estimate"
    assert result.requirements[0].description == "Report mass."


@pytest.mark.parametrize("label", ["initial_searches", "`synthesis_indices`", "build_ids", "get_neighbors"])
def test_internal_protocol_labels_fail_native_definition_validation(label):
    from pydantic import ValidationError
    from src.api.rag.modes.agentic.tools import define_requirements
    with pytest.raises(ValidationError) as caught:
        define_requirements.args_schema.model_validate({"descriptions": [label], "initial_searches": []})
    assert caught.value.errors(include_input=False)[0]["type"] == "internal_tool_requirement"
    # Only standalone labels are blocked; ordinary descriptive prose remains valid.
    parsed = define_requirements.args_schema.model_validate({
        "descriptions": [f"Explain what {label} represents in the requested workflow."], "initial_searches": []})
    assert parsed.descriptions


def test_repeated_protocol_requirement_uses_only_existing_correction_and_no_search(monkeypatch):
    bad = {"descriptions": ["initial_searches"], "initial_searches": []}
    model = FakeToolCallingModel([call("define_requirements", bad, "bad1"),
                                  call("define_requirements", bad, "bad2")], define=False)
    result = run(model, monkeypatch)
    assert result.execution.stop_reason == StopReason.PLANNER_FAILURE
    assert result.execution.requirement_correction_attempts == 1
    assert result.execution.rounds == result.execution.tool_calls == 0
    assert result.requirements == []
    assert len(result.execution.requirement_validation_failures) == 2


def test_second_invalid_definition_stops_with_safe_field_diagnostics(monkeypatch, caplog):
    import json
    secret = "SECRET_MUST_NOT_APPEAR"
    bad = {"descriptions": ["Report mass."], "initial_searches": [
        {"query": secret, "requirement_indices": [], secret: secret}]}
    model = FakeToolCallingModel([call("define_requirements", bad, "bad1"),
                                 call("define_requirements", bad, "bad2"), finish()], define=False)
    result = run(model, monkeypatch)
    assert result.execution.stop_reason == StopReason.PLANNER_FAILURE
    assert result.execution.requirement_correction_attempts == 1
    assert len(result.execution.requirement_validation_failures) == 2
    assert result.execution.tool_calls == result.execution.rounds == 0
    assert result.requirements == []
    assert len(model.seen_messages) == 2
    assert len(model.responses) == 1
    assert secret not in result.execution.model_dump_json()
    assert secret not in caplog.text
    feedback = json.loads(model.seen_messages[1][-1].content)
    assert secret not in json.dumps(feedback)
    assert "<unknown_field>" in json.dumps(feedback)


def test_correction_call_obeys_token_preflight(monkeypatch):
    class CountingModel(FakeToolCallingModel):
        max_tokens = 20

        def get_num_tokens_from_messages(self, messages):
            return 20 if len(messages) <= 2 else 30

        def get_num_tokens(self, text):
            return 10

    model = CountingModel([call("define_requirements", {}, "bad"), finish()], define=False)
    result = run(model, monkeypatch, budget=AgentBudget(max_planner_tokens=315))
    assert result.execution.stop_reason == StopReason.TOKEN_BUDGET
    assert result.execution.requirement_correction_attempts == 0
    assert len(result.execution.requirement_validation_failures) == 1
    assert result.execution.planner_tokens == 15
    assert result.execution.next_call_estimated_tokens == 316
    assert len(model.seen_messages) == 1


def test_correction_call_obeys_time_limit(monkeypatch):
    from src.api.rag.modes.agentic import graph
    clock = Mock(return_value=100.0)
    monkeypatch.setattr("src.api.rag.modes.agentic.executor.monotonic", clock)
    monkeypatch.setattr(graph, "monotonic", clock)

    class ExpiringModel(FakeToolCallingModel):
        def invoke(self, messages):
            result = super().invoke(messages)
            # Let the invalid definition be diagnosed, then expire before the correction.
            clock.side_effect = [100.0, 106.0, 106.0, 106.0]
            return result

    model = ExpiringModel([call("define_requirements", {}, "bad"), finish()], define=False)
    result = run(model, monkeypatch, budget=AgentBudget(max_elapsed_seconds=5))
    assert result.execution.stop_reason == StopReason.TIME_BUDGET
    assert result.execution.requirement_correction_attempts == 0
    assert len(result.execution.requirement_validation_failures) == 1
    assert len(model.seen_messages) == 1


def test_correction_provider_failure_retains_diagnostics(monkeypatch):
    model = FakeToolCallingModel([call("define_requirements", {}, "bad")], define=False)
    result = run(model, monkeypatch)  # Fake model raises when correction is attempted.
    assert result.execution.stop_reason == StopReason.PLANNER_FAILURE
    assert result.execution.requirement_correction_attempts == 1
    assert len(result.execution.requirement_validation_failures) == 1
    assert result.execution.planner_tokens == 15


def test_initial_scope_escape_is_not_retried(monkeypatch):
    model = FakeToolCallingModel([finish()], initial_searches=[{
        "query": "mass", "requirement_indices": [1], "build_ids": ["outside"]}])
    result = run(model, monkeypatch)
    assert result.execution.stop_reason == StopReason.PLANNER_FAILURE
    assert result.execution.requirement_correction_attempts == 0
    assert len(model.seen_messages) == 1


@pytest.mark.parametrize("bad_plan", ["missing_field", "protocol_label"])
def test_native_sdk_sends_paired_definition_error_and_corrected_plan(monkeypatch, bad_plan):
    import json
    import httpx
    from langchain_openai import ChatOpenAI

    requests = []

    def handle(request):
        body = json.loads(request.content)
        requests.append(body)
        index = len(requests)
        name = "define_requirements" if index <= 2 else "finish_with_evidence"
        bad_args = ({"descriptions": ["Report mass."]} if bad_plan == "missing_field" else {
            "descriptions": ["Report mass.", "initial_searches"], "initial_searches": []})
        args = (bad_args if index == 1 else {
            "descriptions": ["Report mass."], "initial_searches": [
                {"query": "mass estimate", "requirement_indices": [1]}]} if index == 2 else {
                    "summary": "Evidence found.", "question_scope": "direct"})
        return httpx.Response(200, json={
            "id": f"chat-{index}", "object": "chat.completion", "created": 0,
            "model": "gpt-5-mini", "choices": [{"index": 0, "finish_reason": "tool_calls",
                "message": {"role": "assistant", "content": None, "tool_calls": [{
                    "id": f"call-{index}", "type": "function", "function": {
                        "name": name, "arguments": json.dumps(args)}}]}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        model = ChatOpenAI(model="gpt-5-mini", api_key="offline", max_retries=0,
                           max_completion_tokens=2000, http_client=client)
        result = run(model, monkeypatch)
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert result.execution.requirement_correction_attempts == 1
    assert len(requests) == 3
    for body in requests[:2]:
        assert body["tool_choice"]["function"]["name"] == "define_requirements"
        assert body["parallel_tool_calls"] is False
        assert [tool["function"]["name"] for tool in body["tools"]] == ["define_requirements"]
    feedback = requests[1]["messages"][-1]
    assert feedback["role"] == "tool"
    assert feedback["tool_call_id"] == "call-1"
    assert json.loads(feedback["content"])["issues"] == [
        {"field": "initial_searches", "code": "missing",
         "message": "Supply the required field at this path in the corrected definition."}
        if bad_plan == "missing_field" else
        {"field": "descriptions[1]", "code": "internal_tool_requirement",
         "message": "Replace the standalone protocol label with a user-requested scientific fact."}]
    assert result.execution.planner_tokens == 45
