import json
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from src.api.rag.contracts import (
    EvidenceChunk,
    FederatedRetrievalScope,
    RetrievalScope,
    ScopedBuild,
)
from src.api.rag.modes.agentic.tools import TERMINAL_TOOLS, build_retrieval_tools


def test_model_sees_small_individual_tool_schemas():
    scope = RetrievalScope("papers", ("build",), builds=(
        ScopedBuild("build", "paper"),
    ))
    tools = build_retrieval_tools(
        client=Mock(), catalogue=Mock(), scope=scope, embed=Mock(),
    )
    schemas = {item.name: item.args_schema.model_json_schema() for item in tools}

    assert set(schemas) == {
        "search_papers", "search_chunks", "get_section", "get_neighbors",
    }
    assert set(schemas["search_chunks"]["properties"]) == {
        "need_id", "query", "retrieval_mode", "build_ids", "paper_ids", "limit",
    }
    assert "need_id" in schemas["search_chunks"]["required"]
    assert "query" in schemas["search_chunks"]["required"]
    assert "oneOf" not in str(schemas)
    assert {item.name for item in TERMINAL_TOOLS} == {
        "finish_with_evidence", "abstain",
    }


def test_chunk_tool_federates_across_authorized_collections(monkeypatch):
    scope = FederatedRetrievalScope((
        RetrievalScope("arxiv", ("arxiv-build",), builds=(
            ScopedBuild("arxiv-build", "arxiv-paper"),
        )),
        RetrievalScope("uploads", ("upload-build",), builds=(
            ScopedBuild("upload-build", "upload-paper"),
        )),
    ))

    def search(_client, child, **_kwargs):
        score = 0.5 if child.collection == "arxiv" else 0.8
        return [EvidenceChunk(
            id=f"{child.collection}-point", text=child.collection,
            collection=child.collection, build_id=child.build_ids[0],
            paper_id=child.builds[0].paper_id, score=score,
        )]

    monkeypatch.setattr(
        "src.api.rag.modes.agentic.tools.scoped_chunk_search", search,
    )
    embed = Mock(return_value=[1.0, 0.0])
    tools = build_retrieval_tools(
        client=Mock(), catalogue=Mock(), scope=scope, embed=embed,
    )
    chunk_tool = next(item for item in tools if item.name == "search_chunks")

    _, artifact = chunk_tool.func(
        need_id="cluster_topic", query="clusters", retrieval_mode="hybrid", build_ids=None,
        paper_ids=None, limit=8,
    )

    assert [row["collection"] for row in artifact["chunks"]] == ["uploads", "arxiv"]
    embed.assert_called_once_with("clusters")


def tools_for_test():
    scope = RetrievalScope("papers", ("build",), builds=(ScopedBuild("build", "paper"),))
    return {item.name: item for item in build_retrieval_tools(
        client=Mock(), catalogue=Mock(), scope=scope, embed=Mock(return_value=[1.0]))}


def evidence(index=47, text=None):
    return EvidenceChunk(
        id=f"point-{index}", text=text if text is not None else "Introduction. " * 70 + "Y, Sr, Zr, Ba, La, Ce.",
        collection="papers", build_id="build", paper_id="paper",
        section_header="Results", chunk_index=index, page=2,
    )


def invoke_tool(item, **args):
    return item.invoke({"name": item.name, "id": "test-call", "type": "tool_call",
                        "args": {"need_id": "r1", **args}})


def test_provider_schema_exposes_neighbor_bounds():
    from langchain_core.utils.function_calling import convert_to_openai_tool
    from src.api.rag.tools.neighbor_retrieval import MAX_NEIGHBORS_PER_SIDE

    schema = convert_to_openai_tool(tools_for_test()["get_neighbors"])
    properties = schema["function"]["parameters"]["properties"]
    for field in ("before", "after"):
        assert properties[field]["minimum"] == 0
        assert properties[field]["maximum"] == MAX_NEIGHBORS_PER_SIDE == 5
        assert properties[field]["type"] == "integer"
    assert properties["chunk_index"]["minimum"] == 0


@pytest.mark.parametrize("field,value", [
    ("after", 8), ("before", -1), ("after", True),
    ("before", 1.5), ("chunk_index", -1), ("chunk_index", False),
])
def test_invalid_neighbor_arguments_fail_before_database_access(monkeypatch, field, value):
    backend = Mock()
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_neighbors", backend)
    args = dict(build_id="build", paper_id="paper", chunk_index=47, before=0, after=0)
    args[field] = value
    with pytest.raises(ValidationError):
        invoke_tool(tools_for_test()["get_neighbors"], **args)
    backend.assert_not_called()


@pytest.mark.parametrize("before,after", [(0, 0), (5, 5)])
def test_neighbor_boundaries_are_forwarded_unchanged(monkeypatch, before, after):
    backend = Mock(return_value=[evidence()])
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_neighbors", backend)
    invoke_tool(tools_for_test()["get_neighbors"],
                build_id="build", paper_id="paper", chunk_index=47, before=before, after=after)
    assert backend.call_args.kwargs["before"] == before
    assert backend.call_args.kwargs["after"] == after


@pytest.mark.parametrize("expansion", ["get_neighbors", "get_section"])
def test_expansion_reveals_answer_beyond_search_preview_without_changing_artifact(monkeypatch, expansion):
    row = evidence()
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_chunk_search", Mock(return_value=[row]))
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_neighbors", Mock(return_value=[row]))
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_section", Mock(return_value=[row]))
    tools = tools_for_test()
    search = invoke_tool(tools["search_chunks"], query="neutron capture elements")
    preview = json.loads(search.content)
    assert preview["text_mode"] == "preview"
    assert len(preview["evidence"][0]["text"]) == 700
    assert preview["evidence"][0]["text_truncated"] is True
    assert "Y, Sr, Zr" not in preview["evidence"][0]["text"]

    args = ({"chunk_index": 47, "before": 0, "after": 0} if expansion == "get_neighbors"
            else {"section_header": "Results"})
    expanded = invoke_tool(tools[expansion], build_id="build", paper_id="paper", **args)
    payload = json.loads(expanded.content)
    assert payload["text_mode"] == "expanded"
    assert payload["evidence"][0]["text"] == row.text
    assert payload["evidence"][0]["text_truncated"] is False
    assert payload["evidence"][0]["text_chars"] == len(row.text)
    assert search.artifact == expanded.artifact
    assert expanded.artifact["chunks"][0]["text"] == row.text


def test_expansion_text_budget_prioritizes_anchor_preserves_order_and_full_artifacts(monkeypatch):
    from src.api.rag.modes.agentic.tools import PLANNER_EXPANSION_TEXT_CHARS
    budget = PLANNER_EXPANSION_TEXT_CHARS
    rows = [evidence(46, "x" * budget), evidence(47), evidence(48, "z" * budget)]
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_neighbors", Mock(return_value=rows))
    result = invoke_tool(tools_for_test()["get_neighbors"], build_id="build", paper_id="paper",
                         chunk_index=47, before=1, after=1)
    payload = json.loads(result.content)
    assert payload["text_budget_chars"] == budget
    assert sum(len(row["text"]) for row in payload["evidence"]) == budget
    assert [row["chunk_index"] for row in payload["evidence"]] == [46, 47, 48]
    assert payload["evidence"][1]["text"] == rows[1].text
    assert [row["text_truncated"] for row in payload["evidence"]] == [True, False, True]
    assert [row["text"] for row in result.artifact["chunks"]] == [row.text for row in rows]


def test_section_budget_marks_even_unshown_text_without_changing_full_artifact(monkeypatch):
    from src.api.rag.modes.agentic.tools import PLANNER_EXPANSION_TEXT_CHARS
    budget = PLANNER_EXPANSION_TEXT_CHARS
    rows = [evidence(0, "x" * (budget + 1)), evidence(1, "tail")]
    monkeypatch.setattr("src.api.rag.modes.agentic.tools.scoped_section", Mock(return_value=rows))
    result = invoke_tool(tools_for_test()["get_section"],
                         build_id="build", paper_id="paper", section_header="Results")
    payload = json.loads(result.content)
    assert len(payload["evidence"][0]["text"]) == budget
    assert payload["evidence"][1]["text"] == ""
    assert all(row["text_truncated"] for row in payload["evidence"])
    assert [row["text"] for row in result.artifact["chunks"]] == [row.text for row in rows]
