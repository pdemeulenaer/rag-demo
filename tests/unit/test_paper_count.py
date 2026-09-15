"""The count command is a read-only catalogue query, with no ingestion clients."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.api.papers import __main__ as cli


@pytest.fixture
def catalogue(monkeypatch):
    catalogue = Mock()
    monkeypatch.setattr(cli, "Catalogue", Mock(return_value=catalogue))
    monkeypatch.setattr(cli, "PaperSettings", lambda: SimpleNamespace(PAPERS_DATABASE_URL="unused"))
    monkeypatch.setattr(cli, "ArxivClient", Mock(side_effect=AssertionError("No arXiv calls expected")))
    monkeypatch.setattr("sys.argv", ["papers", "count"])
    return catalogue


@pytest.mark.parametrize("documents,expected", [
    ([], "0\n"),
    ([
        {"source": "arxiv", "status": "ready", "queryable": True},
        {"source": "uploads", "status": "ready", "queryable": True},
        {"source": "arxiv", "status": "pending", "queryable": False},
        {"source": "arxiv", "status": "running", "queryable": False},
        {"source": "uploads", "status": "failed", "queryable": False},
        # A failed replacement must not hide an older, active ready build.
        {"source": "arxiv", "status": "failed", "queryable": True},
    ], "3\n"),
])
def test_count_ready_documents(catalogue, capsys, documents, expected):
    catalogue.inventory.return_value = documents
    cli.main()
    assert capsys.readouterr().out == expected
    assert catalogue.method_calls == [
        ("require_schema", (), {}), ("inventory", (), {}), ("close", (), {}),
    ]


def test_count_closes_catalogue_on_schema_error(catalogue, capsys):
    catalogue.require_schema.side_effect = RuntimeError("Schema not initialized")
    with pytest.raises(RuntimeError, match="Schema not initialized"):
        cli.main()
    catalogue.close.assert_called_once_with()
    catalogue.inventory.assert_not_called()
    assert capsys.readouterr().out == ""
