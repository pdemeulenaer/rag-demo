# poller.py

import time, json, redis, logging
from openai import OpenAI
from qdrant_client import QdrantClient
from src.api.core.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("poller")

# Initialize Redis & clients
r = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB)
client = OpenAI(api_key=config.OPENAI_API_KEY)
q_client = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY)

def process_completed_batch(batch_id, output_file_id):
    # 1. Get the mapping we saved in worker.py
    meta_raw = r.get(f"metadata:{batch_id}")
    if not meta_raw:
        logger.error(f"Missing metadata for batch {batch_id}")
        return
    id_map = json.loads(meta_raw)

    # 2. Download results
    content = client.files.content(output_file_id).text
    for line in content.strip().split('\n'):
        res = json.loads(line)
        custom_id = res['custom_id']
        description = res['response']['body']['choices'][0]['message']['content']
        
        qdrant_point_id = id_map.get(custom_id)
        if qdrant_point_id:
            # 3. Update Qdrant
            q_client.set_payload(
                collection_name=config.QDRANT_COLLECTION_NAME,
                payload={"description": description},
                points=[qdrant_point_id]
            )
    
    # 4. Cleanup Redis
    r.delete(f"metadata:{batch_id}")
    r.srem("pending_openai_batches", batch_id)

def main_loop():
    logger.info("Starting poller loop...")
    while True:
        try:
            # Get all pending batches from Redis
            batch_ids = r.smembers("pending_openai_batches")
            
            for b_id_bytes in batch_ids:
                b_id = b_id_bytes.decode('utf-8')
                
                try:
                    batch = client.batches.retrieve(b_id)
                    
                    if batch.status == "completed":
                        process_completed_batch(b_id, batch.output_file_id)
                    elif batch.status in ["failed", "expired", "cancelled"]:
                        logger.error(f"Batch {b_id} ended with status: {batch.status}")
                        r.srem("pending_openai_batches", b_id) # Remove failed tasks
                
                except openai.NotFoundError:
                    logger.warning(f"Batch {b_id} not found on OpenAI. Removing from Redis.")
                    r.srem("pending_openai_batches", b_id)
                except Exception as e:
                    logger.error(f"Error checking batch {b_id}: {e}")

            time.sleep(30) # Wait before next poll
            
        except Exception as e:
            logger.error(f"Critical error in poller loop: {e}")
            time.sleep(10) # Wait before retrying loop

if __name__ == "__main__":
    main_loop()