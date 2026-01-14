import sys
import redis
from qdrant_client import QdrantClient
from src.api.core.config import config

def check_health():
    try:
        # 1. Check Redis Connection
        r = redis.Redis(
            host=config.REDIS_HOST, 
            port=config.REDIS_PORT, 
            db=config.REDIS_DB,
            socket_connect_timeout=2
        )
        if not r.ping():
            raise Exception("Redis ping failed")
        print("✅ Redis: Connected")

        # 2. Check Qdrant Connection
        q_client = QdrantClient(
            url=config.QDRANT_URL, 
            api_key=config.QDRANT_API_KEY,
            timeout=2
        )
        # Simple call to check if the service is responsive
        q_client.get_collections()
        print("✅ Qdrant: Connected")

        sys.exit(0)  # Success

    except Exception as e:
        print(f"❌ Health Check Failed: {e}")
        sys.exit(1)  # Failure

if __name__ == "__main__":
    check_health()