from unittest.mock import Mock

from src.api.rag.contracts import EvidenceChunk, RetrievalScope, ScopedBuild
from src.api.rag.modes.agentic import executor
from src.api.rag.modes.agentic.contracts import AgentBudget, AgentPlan, StopReason
from src.api.rag.modes.agentic.planner import PlannerCall


def scope():
    return RetrievalScope("papers", ("build-1",), builds=(
        ScopedBuild("build-1", "paper-1"),
    ))


def chunk(point_id="point-1"):
    return EvidenceChunk(
        id=point_id,
        text="The cluster mass is reported as evidence.",
        collection="papers",
        build_id="build-1",
        paper_id="paper-1",
        title="Cluster paper",
        page=3,
        section_header="Results",
        chunk_index=4,
    )


def search_action(action_id="search_1", query="cluster mass"):
    return {
        "action_id": action_id,
        "need_id": "fact",
        "tool": "search_chunks",
        "query": query,
        "retrieval_mode": "hybrid",
        "build_ids": [],
        "paper_ids": [],
        "limit": 5,
    }


def plan(action=None):
    return AgentPlan.model_validate({
        "schema_version": 1,
        "question_scope": "direct",
        "plan_summary": "Find direct evidence for the requested cluster mass.",
        "evidence_needs": [{
            "need_id": "fact",
            "subquestion": "What mass is reported?",
            "success_criteria": "A directly stated mass from a paper chunk.",
            "target_paper_ids": [],
        }],
        "initial_actions": [action or search_action()],
    })


def decision(kind, *, evidence_ids=None, action=None, stop_reason=None):
    satisfied = kind == "synthesize"
    return {
        "schema_version": 1,
        "decision": kind,
        "summary": "Evidence is sufficient." if satisfied else "More evidence is needed.",
        "assessments": [{
            "need_id": "fact",
            "satisfied": satisfied,
            "evidence_ids": evidence_ids or [],
            "missing_evidence": None if satisfied else "A direct supporting chunk.",
        }],
        "next_actions": [action] if action else [],
        "stop_reason": stop_reason,
    }


class FakePlanner:
    def __init__(self, decisions):
        self.decisions = list(decisions)
        self.plan_calls = 0
        self.assess_calls = 0

    def plan(self, question, corpus_scope, budget):
        self.plan_calls += 1
        return PlannerCall(plan(), 10)

    def assess(self, question, initial_plan, evidence, papers, actions, usage, budget):
        from src.api.rag.modes.agentic.contracts import SufficiencyDecision

        self.assess_calls += 1
        return PlannerCall(SufficiencyDecision.model_validate(self.decisions.pop(0)), 5)


def run(monkeypatch, planner, action_result=None, action_error=None, budget=None):
    if action_error:
        monkeypatch.setattr(executor, "_execute_action", Mock(side_effect=action_error))
    else:
        monkeypatch.setattr(
            executor,
            "_execute_action",
            Mock(return_value=(action_result if action_result is not None else [chunk()], [])),
        )
    return executor.run_agentic(
        "What mass is reported?",
        client=Mock(),
        catalogue=Mock(),
        scope=scope(),
        planner=planner,
        embed=Mock(return_value=[1.0]),
        budget=budget or AgentBudget(),
    )


def test_direct_question_synthesizes_after_one_round(monkeypatch):
    planner = FakePlanner([decision("synthesize", evidence_ids=["point-1"],
                                    stop_reason="sufficient")])
    result = run(monkeypatch, planner)

    assert result.should_synthesize is True
    assert result.execution.stop_reason == StopReason.SUFFICIENT
    assert result.execution.rounds == 1
    assert result.execution.tool_calls == 1
    assert result.execution.evidence_count == 1
    assert planner.assess_calls == 1


def test_repeated_action_stops_without_second_tool_call(monkeypatch):
    repeated = search_action("retry_same_search")
    planner = FakePlanner([decision("continue", action=repeated)])
    tool = Mock(return_value=([], []))
    monkeypatch.setattr(executor, "_execute_action", tool)

    result = executor.run_agentic(
        "Question", client=Mock(), catalogue=Mock(), scope=scope(), planner=planner,
        embed=Mock(return_value=[1.0]), budget=AgentBudget(),
    )

    assert result.should_synthesize is False
    assert result.execution.stop_reason == StopReason.REPEATED_ACTION
    assert result.execution.rounds == 2
    assert result.execution.tool_calls == 1
    assert tool.call_count == 1


def test_all_tool_failures_stop_without_sufficiency_call(monkeypatch):
    planner = FakePlanner([])
    result = run(monkeypatch, planner, action_error=RuntimeError("offline"))

    assert result.execution.stop_reason == StopReason.TOOL_FAILURE
    assert result.execution.actions[0].error_type == "RuntimeError"
    assert planner.assess_calls == 0


def test_explicit_abstention_does_not_synthesize(monkeypatch):
    planner = FakePlanner([decision(
        "abstain", stop_reason="insufficient_evidence"
    )])
    result = run(monkeypatch, planner, action_result=[])

    assert result.should_synthesize is False
    assert result.execution.stop_reason == StopReason.INSUFFICIENT_EVIDENCE
    assert result.evidence == []


def test_hallucinated_sufficiency_evidence_fails_closed(monkeypatch):
    planner = FakePlanner([decision("synthesize", evidence_ids=["invented"],
                                    stop_reason="sufficient")])
    result = run(monkeypatch, planner)

    assert result.should_synthesize is False
    assert result.execution.stop_reason == StopReason.PLANNER_FAILURE


def test_narrow_scope_rejects_build_or_paper_outside_corpus():
    corpus = scope()
    for builds, papers in [(["outside"], []), ([], ["outside-paper"])]:
        try:
            executor._narrow_scope(corpus, builds, papers)
        except ValueError as exc:
            assert "outside the approved corpus" in str(exc)
        else:
            raise AssertionError("Out-of-scope filter was accepted")

    narrowed = executor._narrow_scope(corpus, ["build-1"], ["paper-1"])
    assert narrowed.build_ids == ("build-1",)
    assert narrowed.paper_ids == ("paper-1",)


def test_round_budget_terminates_a_continuing_plan(monkeypatch):
    second = search_action("search_2", "cluster radius")
    planner = FakePlanner([decision("continue", action=second)])
    result = run(
        monkeypatch,
        planner,
        budget=AgentBudget(max_rounds=1),
    )

    assert result.should_synthesize is False
    assert result.execution.stop_reason == StopReason.MAX_ROUNDS
    assert result.execution.rounds == 1


def test_repeated_evidence_stops_as_no_progress(monkeypatch):
    second = search_action("search_2", "cluster radius")
    planner = FakePlanner([decision("continue", action=second)])
    tool = Mock(return_value=([chunk()], []))
    monkeypatch.setattr(executor, "_execute_action", tool)

    result = executor.run_agentic(
        "Question", client=Mock(), catalogue=Mock(), scope=scope(), planner=planner,
        embed=Mock(return_value=[1.0]), budget=AgentBudget(),
    )

    assert result.should_synthesize is False
    assert result.execution.stop_reason == StopReason.NO_PROGRESS
    assert result.execution.rounds == 2
    assert result.execution.evidence_count == 1
    assert tool.call_count == 2
