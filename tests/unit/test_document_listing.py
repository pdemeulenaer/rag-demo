import asyncio
import importlib
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi import FastAPI
import httpx
import pytest


@pytest.fixture
def listing(monkeypatch):
    # Exercise HTTP routing/serialization without depending on sandbox worker threads.
    async def inline(function, *args, **kwargs):
        return function(*args, **kwargs)
    monkeypatch.setattr("fastapi.routing.run_in_threadpool", inline)
    for key in ["OPENAI_API_KEY", "GROQ_API_KEY", "COHERE_API_KEY", "LANGSMITH_API_KEY"]:
        monkeypatch.setenv(key, "offline-test")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("QDRANT_PORT", "6333")
    monkeypatch.setenv("QDRANT_API_KEY", "")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    module = importlib.import_module("src.api.api.system_router")
    client = Mock()
    client.collection_exists.return_value = True
    monkeypatch.setattr(module, "QdrantClient", Mock(return_value=client))
    return module, client


def get_documents(module):
    app = FastAPI()
    app.include_router(module.router)

    async def request():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.get("/documents")
    return asyncio.run(request())


def point(**payload):
    return SimpleNamespace(payload=payload)


def test_documents_route_paginates_and_groups_pdf_chunks(listing):
    module, client = listing
    client.scroll.side_effect = [
        ([point(file_hash="a", file_title="Paper A"), point(file_hash="a", file_title="Paper A")], "next"),
        ([point(file_hash="b", file_title="Paper B"), point(file_hash="a", file_title="Paper A")], None),
    ]
    response = get_documents(module)
    assert response.status_code == 200
    assert response.json() == {"titles": ["Paper A", "Paper B"], "total_documents": 2}
    assert client.scroll.call_args_list[1].kwargs["offset"] == "next"
    assert client.scroll.call_args.kwargs["collection_name"] == module.config.QDRANT_COLLECTION_NAME
    assert client.scroll.call_args.kwargs["with_vectors"] is False
    client.close.assert_called_once()


def test_documents_supports_legacy_metadata_and_distinct_same_title_pdfs(listing):
    module, client = listing
    client.scroll.return_value = ([
        point(file_hash="a", file_title="Same title"), point(file_hash="b", file_title="Same title"),
        point(file_name="legacy.pdf"), point(file_name="legacy.pdf"),
        point(title="Old title"), point(title="Old title"), point(),
    ], None)
    assert get_documents(module).json() == {
        "titles": ["Old title", "Same title", "Same title", "legacy.pdf"], "total_documents": 4,
    }


def test_missing_upload_collection_is_empty_not_404(listing):
    module, client = listing
    client.collection_exists.return_value = False
    response = get_documents(module)
    assert response.status_code == 200
    assert response.json() == {"titles": [], "total_documents": 0}
    client.scroll.assert_not_called()
    client.close.assert_called_once()


def test_qdrant_failure_is_503_without_leaking_connection_details(listing):
    module, client = listing
    client.scroll.side_effect = RuntimeError("sensitive connection details")
    response = get_documents(module)
    assert response.status_code == 503
    assert "sensitive" not in response.text
    client.close.assert_called_once()
