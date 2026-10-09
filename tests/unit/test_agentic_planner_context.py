"""Planner-only compaction keeps native protocol, scope identities and original artifacts."""
import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.api.rag.modes.agentic.contracts import AnswerRequirement
from src.api.rag.modes.agentic.planner_context import compact_planner_messages, RECOVERY_TEXT_CHARS


def test_compaction_bounds_text_and_preserves_messages_without_mutation():
    chunks = [{"id": f"point-{index}", "build_id": "build", "paper_id": "paper",
               "chunk_index": index, "page": 1, "section_header": "Results",
               "text": "Background. " * 100 + "The parameter sensitivity changes the measured rate.",
               "text_chars": 1253, "text_truncated": False} for index in range(30)]
    payload = json.dumps({"text_mode": "expanded", "evidence": chunks, "papers": []})
    messages = [SystemMessage(content="Safety rules"), HumanMessage(content="Original question"),
                AIMessage(content="", tool_calls=[{"name": "search_chunks", "id": "search",
                          "args": {"query": "parameter sensitivity", "need_id": "r1"}}]),
                ToolMessage(content=payload, name="search_chunks", tool_call_id="search",
                            artifact={"chunks": chunks})]
    compacted = compact_planner_messages(messages, [AnswerRequirement(id="r1", description="Sensitivity")])
    assert compacted[:3] == messages[:3]
    assert compacted[-1].tool_call_id == "search"
    short = json.loads(compacted[-1].content)
    assert sum(len(row["text"]) for row in short["evidence"]) <= RECOVERY_TEXT_CHARS
    assert [row["id"] for row in short["evidence"]] == [row["id"] for row in chunks]
    assert "parameter sensitivity" in short["evidence"][0]["text"]
    assert all(row["text_truncated"] for row in short["evidence"])
    assert messages[-1].content == payload
    assert messages[-1].artifact == {"chunks": chunks}


def test_compaction_deduplicates_only_text_not_tool_protocol_or_evidence_ids():
    row = {"id": "chunk", "build_id": "build", "paper_id": "paper", "text": "Evidence"}
    messages = [ToolMessage(name="search_chunks", tool_call_id="first",
                            content=json.dumps({"evidence": [row], "papers": []})),
                ToolMessage(name="get_neighbors", tool_call_id="later",
                            content=json.dumps({"evidence": [row], "papers": []}))]
    compacted = compact_planner_messages(messages, [])
    first, later = [json.loads(message.content)["evidence"][0] for message in compacted]
    assert first["id"] == later["id"] == "chunk"
    assert first["text"] == ""
    assert first["text_omitted_reason"] == "duplicate_chunk_in_later_result"
    assert later["text"] == "Evidence"
    assert [message.tool_call_id for message in compacted] == ["first", "later"]


def test_compaction_does_not_rewrite_errors_or_requirement_definition():
    messages = [ToolMessage(name="get_section", tool_call_id="bad", content="Tool error"),
                ToolMessage(name="define_requirements", tool_call_id="define", content="Fixed IDs: r1")]
    assert compact_planner_messages(messages, []) == messages
