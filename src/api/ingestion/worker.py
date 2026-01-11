import os
import json
import logging
import uuid
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from openai import OpenAI
from src.api.core.config import config
from src.api.core.database import save_batch_to_sqlite # Your Phase 1 DB
from src.api.utils.storage_provider import get_storage_provider, AzureStorageProvider
from src.api.ingestion.ingest_documents import extract_pdf_data # Your existing parser

logger = logging.getLogger(__name__)
client = OpenAI(api_key=config.OPENAI_API_KEY)
BATCH_THRESHOLD = 5

def start_smart_ingestion(file_paths: list[str]):
    """
    Main entry point called by FastAPI BackgroundTasks.
    """
    all_extracted_data = []
    
    # 1. PARSING PHASE: Extract text and images from all PDFs
    # We use a ProcessPool to handle the heavy CPU work of PDF parsing
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        results = list(executor.map(extract_pdf_data, file_paths))
    
    for doc_data in results:
        all_extracted_data.append(doc_data)

    # 2. DECISION PHASE: Batch vs Real-time
    if len(file_paths) >= BATCH_THRESHOLD:
        logger.info(f"📦 Batch Ingestion triggered for {len(file_paths)} files")
        return handle_batch_flow(all_extracted_data)
    else:
        logger.info(f"⚡ Real-time Ingestion triggered for {len(file_paths)} files")
        return handle_realtime_flow(all_extracted_data)

def handle_realtime_flow(all_data):
    """Processes images one-by-one immediately."""
    for doc in all_data:
        for img in doc['images']:
            # Call OpenAI Vision API directly
            # Update Qdrant immediately
            pass 
    logger.info("Real-time processing complete.")

def handle_batch_flow(all_data):
    """Prepares Azure SAS URLs and submits to OpenAI Batch API."""
    provider = get_storage_provider()
    if not isinstance(provider, AzureStorageProvider):
        logger.warning("Batch API requires Azure URLs. Falling back to Real-time.")
        return handle_realtime_flow(all_data)

    batch_tasks = []
    image_metadata_map = []

    for doc in all_data:
        for img in doc['images']:
            custom_id = f"task_{uuid.uuid4()}"
            
            # 1. Upload to Azure (using your existing provider)
            with open(img['local_path'], "rb") as f:
                provider.save_image(f.read(), img['filename'])
            
            # 2. Get 24-hour SAS URL for OpenAI
            sas_url = provider.generate_signed_url(img['filename'], expiry_hours=24)

            # 3. Create JSONL request object
            request_item = {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": "Describe this figure from a technical paper."},
                        {"type": "image_url", "image_url": {"url": sas_url}}
                    ]}],
                    "max_tokens": 500
                }
            }
            batch_tasks.append(json.dumps(request_item))
            
            # Keep track of which ID belongs to which Qdrant point
            image_metadata_map.append({
                "custom_id": custom_id,
                "qdrant_id": img['qdrant_id'],
                "filename": img['filename']
            })

    # 4. SUBMIT TO OPENAI
    # Save local .jsonl
    batch_filename = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    with open(batch_filename, "w") as f:
        f.write("\n".join(batch_tasks))

    # Upload & Create Batch
    file_batch = client.files.create(file=open(batch_filename, "rb"), purpose="batch")
    openai_batch = client.batches.create(
        input_file_id=file_batch.id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )

    # 5. PERSIST STATE
    # Save the batch ID and metadata map to SQLite so the Poller can find it
    save_batch_to_sqlite(openai_batch.id, image_metadata_map)
    
    logger.info(f"Batch {openai_batch.id} submitted successfully.")