from pathlib import Path
from unittest.mock import Mock

import pytest


def test_inventory_defaults_to_all_sources_independent_of_query_source(monkeypatch):
    testing = pytest.importorskip("streamlit.testing.v1")
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root / "src/chatbot_ui"))
    response = Mock()
    response.json.return_value = {"source": "all", "total_documents": 3, "queryable_documents": 3,
        "status_counts": {"ready": 3}, "documents": [
            {"title": "Thesis", "source": "uploads", "status": "ready", "queryable": True},
            {"title": "arXiv A", "source": "arxiv", "status": "ready", "queryable": True},
            {"title": "arXiv B", "source": "arxiv", "status": "ready", "queryable": True},
        ]}
    get = Mock(return_value=response)
    post = Mock(side_effect=AssertionError("Inventory must not submit a question or upload"))
    monkeypatch.setattr("requests.get", get)
    monkeypatch.setattr("requests.post", post)
    app = testing.AppTest.from_file(str(root / "src/chatbot_ui/main.py")).run(timeout=10)
    assert not app.exception
    query_source = next(widget for widget in app.selectbox if widget.label == "Query source")
    assert query_source.value == "uploads"
    history = [{"role": "user", "content": "Existing question"}]
    app.session_state.full_conversation = history
    app.session_state.backend_memory = []
    app.session_state.session_id = "existing-session"
    app.session_state.corpus_snapshot = "existing-snapshot"
    next(widget for widget in app.button if widget.label == "Refresh document inventory").click().run(timeout=10)
    assert not app.exception
    assert get.call_args.args[0].endswith("/catalogue")
    assert get.call_args.kwargs["params"] == {"source": "all"}
    assert len(app.dataframe[0].value) == 3
    assert app.session_state.full_conversation == history
    assert app.session_state.session_id == "existing-session"
    assert app.session_state.corpus_snapshot == "existing-snapshot"
    next(widget for widget in app.button if widget.label == "Start new conversation").click().run(timeout=10)
    assert not app.exception
    assert app.session_state.full_conversation == []
    assert app.session_state.backend_memory == []
    assert app.session_state.session_id == ""
    assert "corpus_snapshot" not in app.session_state
    assert len(app.dataframe[0].value) == 3
    get.assert_called_once()
    post.assert_not_called()


def test_agentic_mode_is_submitted_and_execution_summary_is_retained(monkeypatch):
    testing = pytest.importorskip("streamlit.testing.v1")
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root / "src/chatbot_ui"))
    response = Mock(status_code=200, headers={})
    response.json.return_value = {
        "answer": "Grounded answer",
        "sources": [],
        "images": [],
        "chat_history": [],
        "mode": "agentic",
        "corpus_snapshot": "snapshot-1",
        "execution": {
            "question_scope": "cross_paper",
            "plan_summary": "Compare direct evidence from two papers.",
            "stop_reason": "sufficient",
            "rounds": 2,
            "tool_calls": 3,
            "evidence_count": 6,
            "planner_tokens": 450,
            "elapsed_seconds": 4.25,
            "actions": [
                {"action_id": "find", "need_id": "comparison",
                 "tool": "search_papers", "status": "success", "result_count": 2,
                 "evidence_ids": [], "paper_ids": ["paper-1", "paper-2"],
                 "error_type": None},
                {"action_id": "search", "need_id": "comparison",
                 "tool": "search_chunks", "status": "success", "result_count": 6,
                 "evidence_ids": ["one", "two"], "paper_ids": [],
                 "error_type": None},
            ],
        },
    }
    post = Mock(return_value=response)
    monkeypatch.setattr("requests.post", post)
    monkeypatch.setattr("requests.get", Mock())

    app = testing.AppTest.from_file(str(root / "src/chatbot_ui/main.py")).run(timeout=10)
    mode = next(widget for widget in app.radio if widget.label == "Retrieval mode")
    assert mode.options == [
        "Vanilla — dense retrieval",
        "Hybrid — dense + BM25 fusion",
        "Hybrid + Rerank — dense + BM25 + Cohere",
        "Agentic — bounded multi-step retrieval",
    ]

    app.session_state.full_conversation = [{"role": "user", "content": "Old mode"}]
    app.session_state.backend_memory = [{"role": "user", "content": "Old mode"}]
    app.session_state.session_id = "old-mode-session"
    app.session_state.corpus_snapshot = "snapshot-1"
    mode.set_value("agentic").run(timeout=10)
    assert app.session_state.full_conversation == []
    assert app.session_state.backend_memory == []
    assert app.session_state.session_id == ""
    assert app.session_state.corpus_snapshot == "snapshot-1"
    next(widget for widget in app.text_input if widget.label == "💬 Ask a question:").set_value(
        "Compare two papers"
    )
    next(widget for widget in app.button if widget.label == "Ask").click().run(timeout=10)

    assert not app.exception
    payload = post.call_args.kwargs["json"]
    assert payload["mode"] == "agentic"
    assert payload["query"] == "Compare two papers"
    assistant = app.session_state.full_conversation[-1]
    assert assistant["execution"]["stop_reason"] == "sufficient"
    assert any(expander.label == "🧭 Agentic retrieval details" for expander in app.expander)
