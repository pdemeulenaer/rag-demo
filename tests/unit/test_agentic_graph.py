from unittest.mock import Mock

from langchain_core.messages import AIMessage

from src.api.rag.contracts import EvidenceChunk, RetrievalScope, ScopedBuild
from src.api.rag.modes.agentic.contracts import AgentBudget, StopReason
from src.api.rag.modes.agentic.executor import run_agentic
from src.api.rag.modes.agentic.policies import narrow_scope


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


def search(call_id="call_search", query="cluster mass"):
    return call("search_chunks", {
        "query": query, "retrieval_mode": "hybrid",
        "build_ids": [], "paper_ids": [], "limit": 5,
    }, call_id)


def finish(call_id="call_finish"):
    return call("finish_with_evidence", {
        "summary": "Direct evidence was found.", "question_scope": "direct",
    }, call_id)


class FakeToolCallingModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.bound_tools = []

    def bind_tools(self, tools):
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
    assert result.execution.rounds == 1
    assert result.execution.tool_calls == 1
    assert result.execution.evidence_count == 1
    assert result.execution.planner_tokens == 30
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

    assert result.should_synthesize is False
    assert result.execution.stop_reason == StopReason.REPEATED_ACTION
    assert result.execution.rounds == 1
    assert result.execution.tool_calls == 1
    assert tool.call_count == 1


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
    assert result.execution.rounds == 1
    assert result.execution.tool_calls == 1


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
