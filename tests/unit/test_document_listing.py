import asyncio
import importlib
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
    import src.api.api.papers_router as papers_router
    catalogue = Mock()
    catalogue.inventory.return_value = []
    monkeypatch.setattr(papers_router, "Catalogue", Mock(return_value=catalogue))
    return module, catalogue


def get_documents(module):
    app = FastAPI()
    app.include_router(module.router)

    async def request():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.get("/documents")
    return asyncio.run(request())


def test_documents_route_uses_sql_ready_uploads(listing):
    module, catalogue = listing
    catalogue.inventory.return_value = [
        {"title": "Ready", "status": "ready", "queryable": True},
        {"title": "Pending", "status": "pending", "queryable": False},
    ]
    response = get_documents(module)
    assert response.status_code == 200
    assert response.json() == {"titles": ["Ready"], "total_documents": 1}
    catalogue.inventory.assert_called_once_with("uploads")
    catalogue.close.assert_called_once()


def test_global_inventory_reports_all_processing_states(listing):
    _, catalogue = listing
    from src.api.api.papers_router import inventory_response
    catalogue.inventory.return_value = [
        {"title": "Upload", "status": "waiting_batch", "queryable": False},
        {"title": "arXiv", "status": "ready", "queryable": True},
        {"title": "Replacement", "status": "failed", "queryable": True},
    ]
    result = inventory_response()
    assert result["total_documents"] == 3
    assert result["queryable_documents"] == 2
    assert result["status_counts"] == {"waiting_batch": 1, "ready": 1, "failed": 1}
    catalogue.inventory.assert_called_once_with("all")


def test_empty_upload_catalogue_is_empty_not_404(listing):
    module, catalogue = listing
    response = get_documents(module)
    assert response.status_code == 200
    assert response.json() == {"titles": [], "total_documents": 0}
    catalogue.close.assert_called_once()


def test_catalogue_failure_is_503_without_leaking_connection_details(listing):
    module, catalogue = listing
    catalogue.require_schema.side_effect = RuntimeError("sensitive connection details")
    response = get_documents(module)
    assert response.status_code == 503
    assert "sensitive" not in response.text
    catalogue.close.assert_called_once()
