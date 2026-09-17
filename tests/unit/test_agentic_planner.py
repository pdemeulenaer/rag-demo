from types import SimpleNamespace
from unittest.mock import Mock

from src.api.rag.contracts import RetrievalScope, ScopedBuild
from src.api.rag.modes.agentic.contracts import AgentBudget
from src.api.rag.modes.agentic.planner import OpenAIAgentPlanner


def test_openai_planner_uses_strict_schema_and_reports_tokens(monkeypatch):
    content = """{
      "schema_version": 1,
      "question_scope": "direct",
      "plan_summary": "Find one directly supporting chunk.",
      "evidence_needs": [{
        "need_id": "fact",
        "subquestion": "What is reported?",
        "success_criteria": "A directly supporting chunk.",
        "target_paper_ids": []
      }],
      "initial_actions": [{
        "action_id": "search",
        "need_id": "fact",
        "tool": "search_chunks",
        "query": "reported result",
        "retrieval_mode": "hybrid",
        "build_ids": [],
        "paper_ids": [],
        "limit": 5
      }]
    }"""
    response = SimpleNamespace(
        usage=SimpleNamespace(total_tokens=37),
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
    )
    create = Mock(return_value=response)
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(
        "src.api.rag.modes.agentic.planner.openai_client", Mock(return_value=client)
    )
    planner = OpenAIAgentPlanner(
        model="gpt-5-mini", reasoning_effort="minimal", max_completion_tokens=900
    )
    corpus = RetrievalScope("papers", ("build-1",), builds=(
        ScopedBuild("build-1", "paper-1"),
    ))

    result = planner.plan("What is reported?", corpus, AgentBudget())

    assert result.tokens == 37
    assert result.value.initial_actions[0].tool == "search_chunks"
    request = create.call_args.kwargs
    assert request["reasoning_effort"] == "minimal"
    assert request["max_completion_tokens"] == 900
    schema = request["response_format"]["json_schema"]
    assert schema["strict"] is True
    assert schema["schema"] == result.value.__class__.model_json_schema()
