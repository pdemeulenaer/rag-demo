import pytest
from pydantic import ValidationError

from src.api.rag.modes.agentic.contracts import (
    AgentActionRecord,
    AgentBudget,
    AgentExecutionMetadata,
)


def test_budget_and_public_metadata_remain_strict():
    with pytest.raises(ValidationError):
        AgentBudget(max_rounds=4)
    with pytest.raises(ValidationError):
        AgentExecutionMetadata(
            question_scope="direct", plan_summary="Safe summary", stop_reason="sufficient",
            rounds=1, tool_calls=1, evidence_count=1, planner_tokens=10,
            elapsed_seconds=0.1, actions=[], hidden_reasoning="not allowed",
        )


def test_action_record_accepts_langchain_tool_call_ids():
    record = AgentActionRecord(
        action_id="call_abc-123", tool="search_chunks", status="success",
        result_count=1, evidence_ids=["point"], paper_ids=["paper"], error_type=None,
    )
    assert record.need_id == "graph"
