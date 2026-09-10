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
from uuid import uuid5, NAMESPACE_URL

from src.api.core.config import config
from src.api.core.storage import get_storage_provider
from src.api.rag.utils.utils import prompt_template_config
from src.api.ingestion.common import build_point_payload

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
    threshold = config.INGESTION_BATCH_THRESHOLD
    
    logger.info(f"🧠 Smart Ingestion: Analyzing {count} files (Threshold: {threshold})")

    if count < threshold:
        # --- PATH A: REAL-TIME ---
        logger.info(f"⚡ Mode: Real-time. Processing immediately.")
        for path in file_paths:
            try:
                # Calls your original script's main function
                ingest_documents(file_path=path, verbose=False)
            except Exception as e:
                logger.error(f"Failed to ingest {path}: {e}")
    else:
        # --- PATH B: BATCH ---
        logger.info(f"📦 Mode: OpenAI Batch. Offloading image analysis.")
        trigger_batch_ingestion(file_paths)


# def trigger_batch_ingestion(file_paths: list[str]):
#     """
#     Hybrid Approach:
#     1. Extracts content from all PDFs.
#     2. Upserts Text & Metadata to Qdrant immediately (fast).
#     3. Queues Images for OpenAI Batch API (handles 429s/cost).
#     """
#     qdrant = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY)
#     embedding_model = OpenAIEmbeddings()
    
#     batch_tasks = []
#     image_metadata_map = {} # Maps task_id -> metadata for retrieval later
    
#     for file_path in file_paths:
#         try:
#             filename = os.path.basename(file_path)
#             file_hash = get_file_hash(file_path)
            
#             # A. RAW CONTENT EXTRACTION
#             text_chunks, raw_images, first_pages_text, _ = extract_raw_content(file_path, file_hash)

#             # B. TEXT & METADATA (Immediate)
#             # Get document summary/metadata via Groq
#             meta = extract_metadata_fast(first_pages_text)
            
#             base_info = f"Title: {meta.title}\nAuthors: {', '.join(meta.authors)}\n"
            
#             # Embed and Upsert Text
#             texts_to_embed = [f"{base_info}Content: {t[0]}" for t in text_chunks]
#             if texts_to_embed:
#                 vectors = embedding_model.embed_documents(texts_to_embed)
                
#                 points = []
#                 common_payload = {
#                     "file_name": filename, 
#                     "file_hash": file_hash, 
#                     "title": meta.title,
#                     "year": meta.publication_year, 
#                     "type": "chunk"
#                 }
                
#                 for i, (txt, vec) in enumerate(zip(texts_to_embed, vectors)):
#                     points.append(models.PointStruct(
#                         id=str(uuid.uuid4()),
#                         vector=vec,
#                         payload={**common_payload, "text": txt, "page": text_chunks[i][1]}
#                     ))
                
#                 qdrant.upsert(collection_name=config.QDRANT_COLLECTION_NAME, points=points)
#                 logger.info(f"     ✔ {filename}: Text chunks upserted.")

#             # C. IMAGES (Prepare for Batch API)
#             for img in raw_images:
#                 custom_req_id = f"req_{uuid.uuid4()}"
                
#                 # We send images as Base64 strings inside the Batch JSONL
#                 b64_image = base64.b64encode(img["bytes"]).decode('utf-8')
                
#                 # 1. Load the template
#                 template = prompt_template_config(
#                     config.IMAGE_DESCRIPTION_PROMPT_TEMPLATE_PATH, 
#                     "image_description_generation"
#                 )

#                 # 2. Render the prompts with variables
#                 system_prompt = template["system"].render()
#                 user_prompt = template["user"].render(caption=img['caption'])   

#                 task = {
#                     "custom_id": custom_req_id,
#                     "method": "POST",
#                     "url": "/v1/chat/completions",
#                     "body": {
#                         "model": config.IMAGE_DESCRIPTION_MODEL,
#                         "messages": [
#                             {"role": "system", "content": system_prompt},
#                             {
#                                 "role": "user",
#                                 "content": [
#                                     {"type": "text", "text": user_prompt},
#                                     {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
#                                 ]
#                             }
#                         ],
#                         "max_tokens": 300
#                     }
#                 }

#                 batch_tasks.append(json.dumps(task))
                
#                 # Save metadata for the Poller to re-link results to Qdrant
#                 image_metadata_map[custom_req_id] = {
#                     "file_hash": file_hash,
#                     "file_name": filename,
#                     "caption": img["caption"],
#                     "page_number": img["page_number"],
#                     "title": meta.title,
#                     "image_filename": img["filename"] # The name stored in Azure/Local
#                 }

#         except Exception as e:
#             logger.error(f"Error processing {file_path} for batch: {e}")

#     # D. SUBMIT TO OPENAI
#     if batch_tasks:
#         batch_filename = f"batch_input_{uuid.uuid4()}.jsonl"
#         try:
#             with open(batch_filename, "w") as f:
#                 f.write("\n".join(batch_tasks))
            
#             # 1. Upload file to OpenAI
#             file_obj = client.files.create(file=open(batch_filename, "rb"), purpose="batch")
            
#             # 2. Create the Batch Job
#             batch_job = client.batches.create(
#                 input_file_id=file_obj.id,
#                 endpoint="/v1/chat/completions",
#                 completion_window="24h"
#             )
            
#             # 3. Store job details in Redis for the Poller
#             r.sadd("pending_openai_batches", batch_job.id)
#             r.set(f"batch_meta:{batch_job.id}", json.dumps(image_metadata_map), ex=172800) # 48h expiry
            
#             logger.info(f"🚀 Batch {batch_job.id} submitted with {len(batch_tasks)} images.")

#         except Exception as e:
#             logger.error(f"Failed to submit OpenAI Batch: {e}")
#         finally:
#             if os.path.exists(batch_filename):
#                 os.remove(batch_filename)
#     else:
#         logger.info("No images found to process in this batch.")
def trigger_batch_ingestion(file_paths: list[str]):
    """Use the shared catalogue lifecycle; text stays hidden until figures complete."""
    from src.api.papers.uploads import run_uploads
    return run_uploads(file_paths, mode="batch")


def _trigger_batch_ingestion_legacy(file_paths: list[str]):
    """
    Hybrid ingestion used when the number of uploaded PDFs exceeds the
    ``config.INGESTION_BATCH_THRESHOLD``.
    It:
    1️⃣  Extracts raw text, images and the first‑pages text.
    2️⃣  Runs fast metadata extraction (title, authors, keywords, year, summary).
    3️⃣  Immediately embeds **text chunks** and upserts them to Qdrant.
    4️⃣  Packages every image as a JSON‑L request for the OpenAI Batch API.
    5️⃣  Stores a *rich* metadata map in Redis so the poller can reconstruct a
        **identical payload** to the real‑time path.
    """
    qdrant = QdrantClient(
        url=config.QDRANT_URL,
        port=config.qdrant_port,
        api_key=config.QDRANT_API_KEY,
    )
    embedding_model = OpenAIEmbeddings()

    batch_tasks: list[str] = []
    # The map that the poller will read later.
    # It now contains **all** document‑level fields required by the payload.
    image_metadata_map: dict[str, dict] = {}

    for file_path in file_paths:
        try:
            filename = os.path.basename(file_path)
            file_hash = get_file_hash(file_path)

            # -------------------------------------------------
            # 1️⃣  Raw extraction (text chunks + images)
            # -------------------------------------------------
            text_chunks, raw_images, first_pages_text, _ = extract_raw_content(file_path, file_hash)

            # -------------------------------------------------
            # 2️⃣  Fast metadata extraction (title, authors, …)
            # -------------------------------------------------
            meta = extract_metadata_fast(first_pages_text)

            # -------------------------------------------------
            # 3️⃣  Text up‑insert (immediate)
            # -------------------------------------------------
            if text_chunks:
                # ---- 1️⃣  Gather raw texts and payloads (no PointStruct yet) ----
                texts_to_embed: list[str] = []
                payloads:      list[dict] = []
                point_ids:     list[str] = []

                for idx, (chunk_text, page_num) in enumerate(text_chunks):
                    # Build the searchable text that will be embedded
                    searchable = (
                        f"Title: {meta.title}\n"
                        f"Authors: {', '.join(meta.authors)}\n"
                        f"Content: {chunk_text}"
                    )
                    texts_to_embed.append(searchable)

                    # Deterministic ID – safe for retries
                    # point_id = f"{file_hash}_txt_{page_num}_{idx}"
                    # Deterministic, valid & idempotent UUID for the point
                    point_id = str(uuid5(NAMESPACE_URL, f"{file_hash}_txt_{page_num}_{idx}"))
                    point_ids.append(point_id)

                    # Use the shared helper to create a consistent payload
                    payload = build_point_payload(
                        file_name=filename,
                        file_hash=file_hash,
                        doc_meta=meta,
                        text=searchable,
                        point_type="chunk",
                        img_page=page_num,
                    )
                    # Legacy keys that downstream code still expects
                    payload["summary"] = ""                # will be overwritten later (or stay empty)
                    payload["page_number"] = str(page_num)

                    payloads.append(payload)

                # ---- 2️⃣  Embed *all* chunk texts in ONE batch ----
                vectors = embedding_model.embed_documents(texts_to_embed)

                # ---- 3️⃣  Build the PointStructs **with** their vectors ----
                points = [
                    models.PointStruct(id=pid, vector=vec, payload=pld)
                    for pid, vec, pld in zip(point_ids, vectors, payloads)
                ]

                # ---- 4️⃣  Upsert the chunk points ----
                qdrant.upsert(collection_name=config.QDRANT_COLLECTION_NAME, points=points)
                logger.info(f"     ✔ {filename}: {len(points)} text chunks upserted.")

            # -------------------------------------------------
            # 3️⃣b  Summary point (identical to real‑time flow)
            # -------------------------------------------------
            # Build a human‑readable summary that the real‑time pipeline stores.
            # `meta` already contains title, authors, keywords, publication_year and summary.
            summary_text = (
                f"Title: {meta.title}\n"
                f"Authors: {', '.join(meta.authors)}\n"
                f"Keywords: {', '.join(meta.keywords)}\n"
                f"Year: {meta.publication_year}\n"
                f"Summary: {meta.summary}"
            )

            # Use the shared helper to create a consistent payload.
            summary_payload = build_point_payload(
                file_name=filename,
                file_hash=file_hash,
                doc_meta=meta,
                text=summary_text,
                point_type="summary",
            )

            # Preserve the legacy fields that other parts of the code may still read.
            summary_payload["page_number"] = "0"          # legacy key – not used by the poller
            summary_payload["summary"] = "FULL_DOC"      # legacy flag
            summary_payload["image_path"] = None         # legacy key (figures only use it)

            # Embed the summary (single‑item batch is fine).
            summary_vector = embedding_model.embed_query(summary_text)

            # Deterministic ID – makes the operation idempotent if the batch is retried.
            # summary_point_id = f"{file_hash}_summary"
            summary_point_id = str(uuid5(NAMESPACE_URL, f"{file_hash}_summary"))

            # Upsert the summary point to Qdrant.
            qdrant.upsert(
                collection_name=config.QDRANT_COLLECTION_NAME,
                points=[
                    models.PointStruct(
                        id=summary_point_id,
                        vector=summary_vector,
                        payload=summary_payload,
                    )
                ],
            )
            logger.info(f"     ✔ {filename}: Summary point upserted.")                

            # -------------------------------------------------
            # 4️⃣  Prepare image batch tasks
            # -------------------------------------------------
            for img in raw_images:
                custom_req_id = f"req_{uuid.uuid4()}"

                # Encode image as base64 for the JSON‑L batch
                b64_image = base64.b64encode(img["bytes"]).decode("utf-8")

                # Load the prompt template once per image
                template = prompt_template_config(
                    config.IMAGE_DESCRIPTION_PROMPT_TEMPLATE_PATH,
                    "image_description_generation",
                )
                system_prompt = template["system"].render()
                user_prompt = template["user"].render(caption=img["caption"])

                task = {
                    "custom_id": custom_req_id,
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": config.IMAGE_DESCRIPTION_MODEL,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": user_prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{b64_image}"
                                        },
                                    },
                                ]
                            },
                        ],
                        "max_tokens": 300,
                    },
                }

                batch_tasks.append(json.dumps(task))

                # Store **full** metadata for the poller.
                image_metadata_map[custom_req_id] = {
                    "file_hash": file_hash,
                    "file_name": filename,
                    "title": meta.title,
                    "authors": meta.authors,
                    "keywords": meta.keywords,
                    "year": meta.publication_year,
                    "caption": img["caption"],
                    "page_number": img["page_number"],
                    "image_filename": img["filename"],
                }

        except Exception as exc:
            logger.error(f"Error preparing batch ingestion for {file_path}: {exc}")

    # -------------------------------------------------
    # 5️⃣  Submit the JSON‑L batch to OpenAI
    # -------------------------------------------------
    if not batch_tasks:
        logger.info("🚫 No images to process – batch ingestion skipped.")
        return

    batch_filename = f"batch_input_{uuid.uuid4()}.jsonl"
    try:
        # Write the JSON‑L file
        with open(batch_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(batch_tasks))

        # Upload the file to OpenAI
        file_obj = client.files.create(file=open(batch_filename, "rb"), purpose="batch")

        # Create the batch job (24‑hour completion window)
        batch_job = client.batches.create(
            input_file_id=file_obj.id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
        )

        # Persist the batch ID and the rich metadata map in Redis
        r.sadd("pending_openai_batches", batch_job.id)
        r.set(
            f"batch_meta:{batch_job.id}",
            json.dumps(image_metadata_map),
            ex=172800,  # 48 h TTL – matches the OpenAI 24 h window + safety margin
        )
        # Log Redis connection details and confirm metadata storage
        logger.info(
            f"✅ Stored metadata for batch {batch_job.id} (entries={len(image_metadata_map)}) "
            f"on Redis {config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}"
        )

        logger.info(
            f"🚀 OpenAI batch {batch_job.id} submitted with {len(batch_tasks)} image tasks."
        )
    except Exception as exc:
        logger.error(f"Failed to submit OpenAI batch: {exc}")
    finally:
        # Clean‑up the temporary JSON‑L file
        if os.path.exists(batch_filename):
            os.remove(batch_filename)










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
