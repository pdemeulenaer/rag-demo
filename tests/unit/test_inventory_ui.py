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
