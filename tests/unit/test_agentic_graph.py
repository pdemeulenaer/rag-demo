from unittest.mock import Mock
from types import SimpleNamespace

from langchain_core.messages import AIMessage

from src.api.rag.contracts import EvidenceChunk, RetrievalScope, ScopedBuild
from src.api.rag.modes.agentic.contracts import AgentBudget, StopReason
from src.api.rag.modes.agentic.executor import run_agentic
from src.api.rag.modes.agentic.policies import action_fingerprint, narrow_scope


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
    def __init__(self, responses, requirements=("Report the mass.",), *, define=True):
        self.responses = ([call("define_requirements", {"descriptions": list(requirements)},
                                "define")] if define else []) + list(responses)
        self.bound_tools = []
        self.bind_options = []

    def bind_tools(self, tools, **kwargs):
        self.bind_options.append(kwargs)
        self.bound_tools = tools
        return self

    def invoke(self, messages):
        return self.responses.pop(0)


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
        "define_requirements", "finish_with_evidence", "abstain",
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


def test_agent_cannot_finish_with_an_atomic_need_that_has_no_evidence(monkeypatch):
    search_tool = Mock(side_effect=[[chunk()], []])
    monkeypatch.setattr(
        "src.api.rag.modes.agentic.tools.scoped_chunk_search", search_tool,
    )
    model = FakeToolCallingModel(
        [finish()], requirements=("Report the mass.", "Report the radius."))

    result = run_agentic(
        "Report the mass and radius.", client=Mock(), catalogue=Mock(), scope=scope(),
        embed=Mock(return_value=[1.0]), model=model, budget=AgentBudget(),
    )

    assert result.should_synthesize is True
    assert result.execution.stop_reason == StopReason.INSUFFICIENT_EVIDENCE
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


def test_retrieval_before_requirement_definition_is_rejected(monkeypatch):
    result = run(FakeToolCallingModel([search()], define=False), monkeypatch)
    assert result.execution.stop_reason == StopReason.PLANNER_FAILURE
    assert result.execution.tool_calls == 0
    assert result.requirements == []


def test_multi_need_question_runs_a_baseline_search_for_every_requirement(monkeypatch):
    result = run(FakeToolCallingModel(
        [search(), finish()], requirements=("Report the mass.", "Report the age.")),
        monkeypatch)
    assert [row.id for row in result.requirements] == ["r1", "r2"]
    assert [row.need_id for row in result.execution.actions[:2]] == ["r1", "r2"]
    assert [row.query for row in result.execution.actions[:2]] == [
        "Report the mass.", "Report the age.",
    ]
    assert result.execution.missing_evidence_need_ids == []
    assert result.should_synthesize is True
    assert result.execution.synthesis_policy == "model_finish"


def test_coverage_first_stops_safely_when_tool_budget_cannot_cover_all_needs(monkeypatch):
    result = run(FakeToolCallingModel(
        [finish()], requirements=("Report the mass.", "Report the age.")),
        monkeypatch, budget=AgentBudget(max_tool_calls=1))

    assert result.execution.stop_reason == StopReason.TOOL_CALL_BUDGET
    assert result.execution.tool_calls == 1
    assert [row.need_id for row in result.execution.actions] == ["r1"]
    assert result.execution.missing_evidence_need_ids == ["r2"]
    assert result.should_synthesize is True


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
