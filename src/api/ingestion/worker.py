# src/api/ingestion/worker.py

import os
import json
import uuid
import logging
import redis
import base64
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from qdrant_client import QdrantClient, models

from src.api.core.config import config
from src.api.core.storage import get_storage_provider

# [IMPORT HARMONIZATION]
# Reusing the robust extraction and processing logic from your existing script
from src.api.ingestion.ingest_documents import (
    ingest_documents,          # The full sync pipeline
    extract_raw_content,       # The extraction logic
    extract_metadata_fast,     # The fast metadata logic
    get_file_hash,             # Hash utility
    OpenAIEmbeddings           # Your embedding class
)

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Clients
client = OpenAI(api_key=config.OPENAI_API_KEY)
r = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB)

def start_smart_ingestion(file_paths: list[str]):
    """
    The Main Conductor.
    Decides between Real-time (Sync) and Batch (Async) based on volume.
    """
    count = len(file_paths)
    threshold = config.BATCH_THRESHOLD
    
    logger.info(f"🧠 Smart Ingestion: Analyzing {count} files (Threshold: {threshold})")

    if count < threshold:
        # --- PATH A: REAL-TIME ---
        logger.info(f"⚡ Mode: Real-time. Processing immediately.")
        for path in file_paths:
            try:
                # Calls your original script's main function
                ingest_documents(
                    file_path=path, 
                    qdrant_url=config.QDRANT_URL, 
                    qdrant_api_key=config.QDRANT_API_KEY, 
                    collection_name=config.QDRANT_COLLECTION_NAME
                )
            except Exception as e:
                logger.error(f"Failed to ingest {path}: {e}")
    else:
        # --- PATH B: BATCH ---
        logger.info(f"📦 Mode: OpenAI Batch. Offloading image analysis.")
        trigger_batch_ingestion(file_paths)


def trigger_batch_ingestion(file_paths: list[str]):
    """
    Hybrid Approach:
    1. Extracts content from all PDFs.
    2. Upserts Text & Metadata to Qdrant immediately (fast).
    3. Queues Images for OpenAI Batch API (handles 429s/cost).
    """
    qdrant = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY)
    embedding_model = OpenAIEmbeddings()
    
    batch_tasks = []
    image_metadata_map = {} # Maps task_id -> metadata for retrieval later
    
    for file_path in file_paths:
        try:
            filename = os.path.basename(file_path)
            file_hash = get_file_hash(file_path)
            
            # A. RAW CONTENT EXTRACTION
            text_chunks, raw_images, first_pages_text, _ = extract_raw_content(file_path, file_hash)

            # B. TEXT & METADATA (Immediate)
            # Get document summary/metadata via Groq
            meta = extract_metadata_fast(first_pages_text)
            
            base_info = f"Title: {meta.title}\nAuthors: {', '.join(meta.authors)}\n"
            
            # Embed and Upsert Text
            texts_to_embed = [f"{base_info}Content: {t[0]}" for t in text_chunks]
            if texts_to_embed:
                vectors = embedding_model.embed_documents(texts_to_embed)
                
                points = []
                common_payload = {
                    "file_name": filename, 
                    "file_hash": file_hash, 
                    "title": meta.title,
                    "year": meta.publication_year, 
                    "type": "chunk"
                }
                
                for i, (txt, vec) in enumerate(zip(texts_to_embed, vectors)):
                    points.append(models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vec,
                        payload={**common_payload, "text": txt, "page": text_chunks[i][1]}
                    ))
                
                qdrant.upsert(collection_name=config.QDRANT_COLLECTION_NAME, points=points)
                logger.info(f"     ✔ {filename}: Text chunks upserted.")

            # C. IMAGES (Prepare for Batch API)
            for img in raw_images:
                custom_req_id = f"req_{uuid.uuid4()}"
                
                # We send images as Base64 strings inside the Batch JSONL
                b64_image = base64.b64encode(img["bytes"]).decode('utf-8')
                
                prompt = (
                    "You are a scientific research assistant. Analyze this figure.\n"
                    f"Caption: \"{img['caption']}\"\n\n"
                    "1. Identify figure type.\n"
                    "2. Describe data trends/relationships.\n"
                    "3. Summarize key insight.\n"
                    "Provide a dense, searchable description."
                )

                task = {
                    "custom_id": custom_req_id,
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": "gpt-4.1-mini", #"gpt-4o-mini", #"gpt-4o", 
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                                ]
                            }
                        ],
                        "max_tokens": 300
                    }
                }
                batch_tasks.append(json.dumps(task))
                
                # Save metadata for the Poller to re-link results to Qdrant
                image_metadata_map[custom_req_id] = {
                    "file_hash": file_hash,
                    "file_name": filename,
                    "caption": img["caption"],
                    "page_number": img["page_number"],
                    "title": meta.title,
                    "image_filename": img["filename"] # The name stored in Azure/Local
                }

        except Exception as e:
            logger.error(f"Error processing {file_path} for batch: {e}")

    # D. SUBMIT TO OPENAI
    if batch_tasks:
        batch_filename = f"batch_input_{uuid.uuid4()}.jsonl"
        try:
            with open(batch_filename, "w") as f:
                f.write("\n".join(batch_tasks))
            
            # 1. Upload file to OpenAI
            file_obj = client.files.create(file=open(batch_filename, "rb"), purpose="batch")
            
            # 2. Create the Batch Job
            batch_job = client.batches.create(
                input_file_id=file_obj.id,
                endpoint="/v1/chat/completions",
                completion_window="24h"
            )
            
            # 3. Store job details in Redis for the Poller
            r.sadd("pending_openai_batches", batch_job.id)
            r.set(f"batch_meta:{batch_job.id}", json.dumps(image_metadata_map), ex=172800) # 48h expiry
            
            logger.info(f"🚀 Batch {batch_job.id} submitted with {len(batch_tasks)} images.")

        except Exception as e:
            logger.error(f"Failed to submit OpenAI Batch: {e}")
        finally:
            if os.path.exists(batch_filename):
                os.remove(batch_filename)
    else:
        logger.info("No images found to process in this batch.")










# # src/api/ingestion/worker.py

# import os
# import json
# import logging
# import uuid
# from concurrent.futures import ProcessPoolExecutor
# from datetime import datetime
# from openai import OpenAI
# import redis

# from src.api.core.config import config
# from src.api.core.database import save_batch_to_sqlite # Your Phase 1 DB
# from src.api.utils.storage_provider import get_storage_provider, AzureStorageProvider
# from src.api.ingestion.ingest_documents import extract_pdf_data # Your existing parser

# logger = logging.getLogger(__name__)
# client = OpenAI(api_key=config.OPENAI_API_KEY)


# # Initialize Redis
# r = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB)

# def start_smart_ingestion(file_paths: list[str]):
#     """
#     Main entry point called by FastAPI BackgroundTasks.
#     """
#     all_extracted_data = []
    
#     # 1. PARSING PHASE: Extract text and images from all PDFs
#     # We use a ProcessPool to handle the heavy CPU work of PDF parsing
#     with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
#         results = list(executor.map(extract_pdf_data, file_paths))
    
#     for doc_data in results:
#         all_extracted_data.append(doc_data)

#     # 2. DECISION PHASE: Batch vs Real-time
#     if len(file_paths) >= config.INGESTION_BATCH_THRESHOLD:
#         logger.info(f"📦 Batch Ingestion triggered for {len(file_paths)} files")
#         return handle_batch_flow(all_extracted_data)
#     else:
#         logger.info(f"⚡ Real-time Ingestion triggered for {len(file_paths)} files")
#         return handle_realtime_flow(all_extracted_data)

# def handle_realtime_flow(all_data):
#     """Processes images one-by-one immediately."""
#     for doc in all_data:
#         for img in doc['images']:
#             # Call OpenAI Vision API directly
#             # Update Qdrant immediately
#             pass 
#     logger.info("Real-time processing complete.")

# def handle_batch_flow(all_data):
#     """Prepares Azure SAS URLs and submits to OpenAI Batch API."""
#     provider = get_storage_provider()
#     if not isinstance(provider, AzureStorageProvider):
#         logger.warning("Batch API requires Azure URLs. Falling back to Real-time.")
#         return handle_realtime_flow(all_data)

#     batch_tasks = []
#     image_metadata_map = {} # Changed to dict for faster O(1) lookup later

#     for doc in all_data:
#         for img in doc['images']:
#             custom_id = f"task_{uuid.uuid4()}"
            
#             # 1. Upload to Azure
#             with open(img['local_path'], "rb") as f:
#                 provider.save_image(f.read(), img['filename'])
            
#             sas_url = provider.generate_signed_url(img['filename'], expiry_hours=24)

#             # 2. JSONL Object
#             request_item = {
#                 "custom_id": custom_id,
#                 "method": "POST",
#                 "url": "/v1/chat/completions",
#                 "body": {
#                     "model": "gpt-4o-mini",
#                     "messages": [{"role": "user", "content": [
#                         {"type": "text", "text": "Describe this figure from a technical paper."},
#                         {"type": "image_url", "image_url": {"url": sas_url}}
#                     ]}],
#                     "max_tokens": 500
#                 }
#             }
#             batch_tasks.append(json.dumps(request_item))
            
#             # Map custom_id -> qdrant_id for the poller
#             image_metadata_map[custom_id] = img['qdrant_id']

#     # 3. SUBMIT TO OPENAI
#     batch_filename = f"batch_{uuid.uuid4()}.jsonl"
#     try:
#         with open(batch_filename, "w") as f:
#             f.write("\n".join(batch_tasks))

#         file_batch = client.files.create(file=open(batch_filename, "rb"), purpose="batch")
#         openai_batch = client.batches.create(
#             input_file_id=file_batch.id,
#             endpoint="/v1/chat/completions",
#             completion_window="24h"
#         )

#         # 4. PERSIST TO REDIS (Atomic Pipeline)
#         with r.pipeline() as pipe:
#             # Track the batch itself
#             pipe.sadd("pending_openai_batches", openai_batch.id)
#             # Store metadata (mapping)
#             pipe.set(f"metadata:{openai_batch.id}", json.dumps(image_metadata_map))
#             pipe.execute()
        
#         logger.info(f"🚀 Batch {openai_batch.id} submitted.")

#     finally:
#         # Cleanup local file to prevent storage bloat in Docker
#         if os.path.exists(batch_filename):
#             os.remove(batch_filename)