from unittest.mock import Mock

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
        "query", "retrieval_mode", "build_ids", "paper_ids", "limit",
    }
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
        query="clusters", retrieval_mode="hybrid", build_ids=None,
        paper_ids=None, limit=8,
    )

    assert [row["collection"] for row in artifact["chunks"]] == ["uploads", "arxiv"]
    embed.assert_called_once_with("clusters")
