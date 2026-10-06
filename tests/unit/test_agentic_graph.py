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
                 initial_searches=(), synthesis_indices=()):
        self.responses = ([call("define_requirements", {
            "descriptions": list(requirements), "initial_searches": list(initial_searches),
            "synthesis_indices": list(synthesis_indices)},
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
    assert len(model.responses) == 1


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
