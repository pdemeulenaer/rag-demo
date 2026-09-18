from unittest.mock import Mock

from src.api.rag.contracts import RetrievalScope, ScopedBuild
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
