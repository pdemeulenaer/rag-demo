import asyncio
from fastapi import APIRouter, status, Response
from qdrant_client import AsyncQdrantClient
import redis.asyncio as redis
from src.api.core.config import config

router = APIRouter()

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
