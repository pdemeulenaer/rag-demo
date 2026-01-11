# src/api/ingestion/poller.py

# This file handles polling OpenAI for batch job completions
# It should be run periodically (e.g., via a cron job or scheduler)

import json
import sqlite3
import logging
import time
from openai import OpenAI
from qdrant_client import QdrantClient
from src.api.core.config import config

# Setup Clients
client = OpenAI(api_key=config.OPENAI_API_KEY)
qdrant_client = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY)
DB_NAME = "jobs.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def poll_and_update():
    """Checks all 'pending' batches and updates Qdrant if they are done."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("SELECT batch_id FROM batches WHERE status='pending'")
        pending_batches = cursor.fetchall()

        if not pending_batches:
            logger.info("No pending batches found.")
            return

        for (batch_id,) in pending_batches:
            logger.info(f"Checking status for batch: {batch_id}")
            
            # 1. Retrieve batch status from OpenAI
            batch_status = client.batches.retrieve(batch_id)
            
            if batch_status.status == "completed":
                handle_completed_batch(batch_id, batch_status.output_file_id, conn)
            elif batch_status.status in ["failed", "expired", "cancelled"]:
                logger.error(f"Batch {batch_id} failed with status: {batch_status.status}")
                conn.execute("UPDATE batches SET status=? WHERE batch_id=?", (batch_status.status, batch_id))
            else:
                logger.info(f"Batch {batch_id} is still {batch_status.status}...")

def handle_completed_batch(batch_id, output_file_id, db_conn):
    """Downloads results and syncs them to Qdrant."""
    logger.info(f"✅ Batch {batch_id} complete! Syncing to Qdrant...")

    # 1. Download the result file (JSONL format)
    file_response = client.files.content(output_file_id)
    results = file_response.text.strip().split('\n')

    for line in results:
        data = json.loads(line)
        custom_id = data.get("custom_id")
        
        # Extract the assistant's response (the image description)
        try:
            description = data['response']['body']['choices'][0]['message']['content']
        except (KeyError, TypeError):
            logger.warning(f"Could not parse response for {custom_id}")
            continue

        # 2. Look up the Qdrant Point ID from our SQLite metadata
        cursor = db_conn.execute(
            "SELECT qdrant_point_id FROM pending_images WHERE custom_id=?", 
            (custom_id,)
        )
        row = cursor.fetchone()
        
        if row:
            qdrant_id = row[0]
            # 3. Update Qdrant Point Payload
            qdrant_client.set_payload(
                collection_name=config.QDRANT_COLLECTION,
                payload={"description": description, "status": "processed"},
                points=[qdrant_id]
            )
            logger.info(f"Updated Qdrant point {qdrant_id} with description.")

    # 4. Mark batch as completed in our DB
    db_conn.execute("UPDATE batches SET status='completed' WHERE batch_id=?", (batch_id,))
    db_conn.commit()

if __name__ == "__main__":
    # In production, use a scheduler. For testing, run once or in a loop.
    while True:
        poll_and_update()
        time.sleep(600)  # Check every 10 minutes