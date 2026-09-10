import asyncio
from contextlib import closing
from fastapi import APIRouter, HTTPException, status, Response
from qdrant_client import AsyncQdrantClient, QdrantClient
import redis.asyncio as redis
from src.api.core.config import config

router = APIRouter()


@router.get("/documents")
def list_documents():
    """List uploaded PDFs, not the separate SQL-backed arXiv corpus."""
    try:
        with closing(QdrantClient(
            url=config.QDRANT_URL, port=config.qdrant_port,
            api_key=config.QDRANT_API_KEY or None, timeout=10,
            check_compatibility=False,
        )) as client:
            collection = config.QDRANT_COLLECTION_NAME
            if not client.collection_exists(collection):
                return {"titles": [], "total_documents": 0}
            documents = {}
            offset = None
            while True:
                points, offset = client.scroll(
                    collection_name=collection, offset=offset, limit=1000,
                    with_payload=["file_hash", "file_name", "file_title", "title"],
                    with_vectors=False,
                )
                for point in points:
                    payload = point.payload or {}
                    title = payload.get("file_title") or payload.get("title") or payload.get("file_name")
                    if not isinstance(title, str) or not title.strip():
                        continue
                    title = title.strip()
                    # Text chunks, summaries and figures belong to the same PDF.
                    identity = ("hash", payload["file_hash"]) if payload.get("file_hash") else (
                        ("name", payload["file_name"]) if payload.get("file_name") else ("title", title)
                    )
                    documents.setdefault(identity, title)
                if offset is None:
                    break
            titles = sorted(documents.values())
            return {"titles": titles, "total_documents": len(titles)}
    except Exception as exc:
        raise HTTPException(503, "Uploaded-PDF catalogue unavailable; check the backend Qdrant connection.") from exc


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Parallel health check for Azure App Service.
    """
    async def check_redis():
        try:
            r = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=0)
            await asyncio.wait_for(r.ping(), timeout=2.0)
            await r.close()
            return "ok"
        except Exception:
            return "unavailable"

    async def check_qdrant():
        try:
            # Note: We use the QDRANT_URL from your config
            q_client = AsyncQdrantClient(
                url=config.QDRANT_URL,
                port=config.qdrant_port,
                api_key=config.QDRANT_API_KEY,
            )
            await asyncio.wait_for(q_client.get_collections(), timeout=2.0)
            await q_client.close()
            return "ok"
        except Exception:
            return "unavailable"

    # Run checks in parallel to minimize latency
    redis_status, qdrant_status = await asyncio.gather(check_redis(), check_qdrant())
    
    health_data = {
        "status": "healthy",
        "redis": redis_status,
        "qdrant": qdrant_status
    }

    if "unavailable" in [redis_status, qdrant_status]:
        health_data["status"] = "unhealthy"
        return Response(content=str(health_data), status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    return health_data
