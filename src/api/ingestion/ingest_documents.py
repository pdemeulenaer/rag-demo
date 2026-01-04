import os
import hashlib
import uuid
import json
import fitz
import pymupdf
import re
import base64
import statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, wait
from concurrent.futures import ProcessPoolExecutor
from typing import List, Tuple, Dict, Any

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from langchain.text_splitter import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import PointStruct
from langchain.embeddings.base import Embeddings
from openai import OpenAI, RateLimitError, APIError
import instructor
from pydantic import BaseModel, Field
import time

from src.api.core.config import config
from src.api.rag.summarize import summarize_text
from src.api.rag.utils.utils import prompt_template_config
from src.api.core.storage import get_storage_provider

# === Config ===
MAX_WORKERS = 40 

# OpenAI Client (For Embeddings & Vision)
client = OpenAI(api_key=config.OPENAI_API_KEY)
openai_client = instructor.from_openai(client)

# Groq Client (For fast Metadata & Summarization)
# We assume config.GROQ_API_KEY exists. 
# groq_client_raw = OpenAI(
#     base_url="https://api.groq.com/openai/v1",
#     api_key=config.GROQ_API_KEY
# )
# groq_client = instructor.from_openai(groq_client_raw)

# Groq Client
groq_client_raw = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=config.GROQ_API_KEY
)

# ✅ FIX: Force Mode.JSON here
groq_client = instructor.from_openai(
    groq_client_raw,
    mode=instructor.Mode.JSON
)

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "authors": {"type": "array", "items": {"type": "string"}},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "publication_year": {"type": "string"},
        "summary": {"type": "string"}
    },
    "required": ["title", "authors", "keywords", "summary"]
}

def to_list(val: str | None) -> list[str]:
    if not val:
        return []
    return [x.strip() for x in re.split(r"[;,]", val) if x.strip()]

class AdditionalMetadata(BaseModel):
    title: str = Field(..., description="The title of the document")
    authors: list[str] = Field(default_factory=list, description="List of authors")
    keywords: list[str] = Field(default_factory=list, description="List of keywords")
    publication_year: str = Field(..., description="The year of publication (e.g., '2023').") 
    summary: str = Field(..., description="A detailed summary of the document.")


# === Helper Functions ===

@retry(retry=retry_if_exception_type((RateLimitError, APIError)), wait=wait_exponential(multiplier=1, min=2, max=20), stop=stop_after_attempt(5))
def describe_image_with_gpt4o(base64_image: str, caption: str = "") -> str:
    """Sends image to GPT-4o for description."""
    prompt = (
        "You are a scientific research assistant. Analyze this figure.\n"
        f"Caption: \"{caption}\"\n\n"
        "1. Identify figure type.\n"
        "2. Describe data trends/relationships.\n"
        "3. Summarize key insight.\n"
        "Provide a dense, searchable description."
    )
    # Use gpt-4o-mini if cost/speed is a priority, otherwise gpt-4o
    response = client.chat.completions.create(
        model="gpt-4.1-mini", #"gpt-4o-mini", #"gpt-4o", 
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}", "detail": "high"}},
                ],
            }
        ],
        max_tokens=300
    )
    return response.choices[0].message.content

# @retry(retry=retry_if_exception_type((RateLimitError, APIError)), wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
# def extract_metadata_fast(text: str) -> AdditionalMetadata:
#     """Uses Groq (Llama-3) for ultra-fast metadata extraction."""
    
#     # Simple prompt for Groq
#     system_prompt = "You are an expert librarian. Extract metadata from this scientific text into JSON."
    
#     return groq_client.chat.completions.create(
#         model="llama3-70b-8192", # Much faster than GPT-4o
#         response_model=AdditionalMetadata,
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": f"Text: {text[:4000]}"}, # Limit text to fit context if needed
#         ],
#         temperature=0.1
#     )

# In your Config or constants
# "openai/gpt-oss-20b" is currently one of the fastest models on Groq (approx 1000 t/s)
METADATA_MODEL_FAST = "openai/gpt-oss-20b" # "llama-3.1-8b-instant" # produces 400 error

@retry(retry=retry_if_exception_type((RateLimitError, APIError)), wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def extract_metadata_fast(text: str) -> AdditionalMetadata:
    """
    Uses Groq with the ultra-fast 'gpt-oss-20b' model for sub-second extraction.
    """
    # system_prompt = "You are an expert librarian. Extract metadata from this scientific text into JSON."
    system_prompt = "You are an expert librarian. Extract metadata from this scientific text. Return ONLY the JSON object."
    # system_prompt = (
    #         "You are an expert librarian. Extract metadata from this text. "
    #         "Your response must be a valid JSON object inside a markdown code block."
    #     )    
    
    return groq_client.chat.completions.create(
        model=METADATA_MODEL_FAST, 
        response_model=AdditionalMetadata,
        messages=[
            {"role": "system", "content": system_prompt},
            # We limit text to 6k char to keep it within the high-speed context window preference
            {"role": "user", "content": f"Text: {text[:6000]}"}, 
        ],
        # Explicitly tell the API to expect a JSON object
        # response_format={"type": "json_object"},        
        temperature=0.1
    )

@retry(retry=retry_if_exception_type((RateLimitError, APIError)), wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def robust_summarize_text(text: str) -> str:
    """Wrapper for summarization using Groq."""
    summary_obj = summarize_text(
        text, provider='groq', model=config.SUMMARIZATION_MODEL,
        temperature=config.SUMMARIZATION_MODEL_TEMPERATURE, 
        max_tokens=config.SUMMARIZATION_MODEL_MAX_TOKENS,
        template_name="document_chunk_summarization",
    )
    return summary_obj.summary.strip()

class OpenAIEmbeddings(Embeddings):
    def __init__(self, model_name: str = "text-embedding-3-small"):
        self.model_name = model_name
        self.client = client
        self.dimensions = 1536

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Check for empty lists to avoid API errors
        if not texts: return []
        batch_size = 100
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            # Replace newlines to improve embedding quality
            batch = [t.replace("\n", " ") for t in batch]
            response = self.client.embeddings.create(input=batch, model=self.model_name)
            all_embeddings.extend([item.embedding for item in response.data])
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]

def get_file_hash(filepath) -> str:
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def get_text_chunks_recursive(text) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=4000, chunk_overlap=400, separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    return splitter.split_text(text)

def identify_figures_on_page(page) -> List[Dict[str, Any]]:
    text_blocks = page.get_text("blocks")
    fig_pattern = re.compile(r"^\s*(?:Fig\.?|Figure|Scheme|Chart|Panel|Box)\s*\d*", re.IGNORECASE)
    captions = []
    
    # 1. Find captions
    for i, block in enumerate(text_blocks):
        if fig_pattern.match(block[4]):
            cap_rect = pymupdf.Rect(block[:4])
            cap_text = block[4].strip().replace("\n", " ")
            for j in range(i + 1, len(text_blocks)):
                next_block = text_blocks[j]
                if (next_block[1] - cap_rect.y1) < 15 and abs(next_block[0] - cap_rect.x0) < 20:
                    cap_rect |= pymupdf.Rect(next_block[:4])
                    cap_text += " " + next_block[4].strip().replace("\n", " ")
                else: break
            captions.append({"rect": cap_rect, "text": cap_text})

    # 2. Find figures based on captions
    figures = []
    for cap in captions:
        search_bottom = cap["rect"].y0
        search_top = 0
        for block in reversed(text_blocks):
            block_rect = pymupdf.Rect(block[:4])
            if block_rect.y1 < search_bottom - 20:
                if len(block[4].strip()) > 100: 
                    search_top = block_rect.y1 + 5
                    break
        
        figure_rect = pymupdf.Rect(page.rect.x0, search_top, page.rect.x1, cap["rect"].y1)
        figure_rect = (figure_rect + (-5, -5, 5, 5)) & page.rect
        figures.append({"rect": figure_rect, "caption": cap["text"]})
    return figures

# === Optimized Extraction ===
# def extract_raw_content(filepath: str, file_hash: str):
#     doc = pymupdf.open(filepath)
#     raw_text_chunks = [] 
#     raw_images = []      
#     first_pages_text = ""
    
#     metadata_fallback = doc.metadata or {}
#     fallback_fig_counter = 1

#     for page_number, page in enumerate(doc, start=1):
#         text = page.get_text()
#         if page_number <= 5: # Only need first 5 for metadata
#             first_pages_text += "\n" + text
        
#         if text.strip():
#             chunks = get_text_chunks_recursive(text)
#             for chunk in chunks:
#                 raw_text_chunks.append((chunk, page_number))

#         figures = identify_figures_on_page(page)
#         for fig in figures:
#             match = re.search(r"(?:Fig(?:\.|ure)?)\s*(\d+)", fig["caption"], re.IGNORECASE)
#             fig_label = match.group(1) if match else f"unlabeled_{fallback_fig_counter}"
#             if not match: fallback_fig_counter += 1

#             try:
#                 # pix = page.get_pixmap(clip=fig["rect"], dpi=150) # DPI 150 is usually sufficient for LLM & faster
#                 pix = page.get_pixmap(clip=fig["rect"], dpi=150, colorspace=fitz.csRGB, alpha=False)
#                 if pix.width < 100 or pix.height < 100: continue
                
#                 # --- Old PNG code ---
#                 # img_bytes = pix.tobytes("png")
#                 # filename = f"{file_hash}_fig_{fig_label}.png"

#                 # --- New JPEG code ---
#                 # We use jpg_quality=80 as it's the "sweet spot": 
#                 # Small enough for fast upload, clear enough for gpt-4o-mini.
#                 img_bytes = pix.tobytes(output="jpg", jpg_quality=80) 
#                 filename = f"{file_hash}_fig_{fig_label}.jpg"
                
#                 raw_images.append({
#                     "bytes": img_bytes,
#                     "filename": filename,
#                     "caption": fig["caption"],
#                     "page_number": page_number
#                 })
#             except Exception: pass

#     return raw_text_chunks, raw_images, first_pages_text, metadata_fallback


def process_single_page(page_data):
    """Worker function to process one page at a time."""
    # Unpack data
    filepath, page_number, file_hash = page_data
    
    # We must open a new doc handle per process/thread for safety
    doc = pymupdf.open(filepath)
    page = doc[page_number - 1] # 0-indexed
    
    local_text_chunks = []
    local_images = []
    
    text = page.get_text()
    
    # 1. Chunking logic (Matches your current per-page style)
    if text.strip():
        chunks = get_text_chunks_recursive(text)
        for chunk in chunks:
            local_text_chunks.append((chunk, page_number))

    # 2. Figure detection
    figures = identify_figures_on_page(page)
    for i, fig in enumerate(figures):
        match = re.search(r"(?:Fig(?:\.|ure)?)\s*(\d+)", fig["caption"], re.IGNORECASE)
        fig_label = match.group(1) if match else f"p{page_number}_{i}"

        try:
            pix = page.get_pixmap(clip=fig["rect"], dpi=150, colorspace=fitz.csRGB, alpha=False)
            if pix.width < 100 or pix.height < 100: continue
            
            img_bytes = pix.tobytes(output="jpg", jpg_quality=80) 
            filename = f"{file_hash}_fig_{fig_label}.jpg"
            
            local_images.append({
                "bytes": img_bytes,
                "filename": filename,
                "caption": fig["caption"],
                "page_number": page_number
            })
        except Exception: pass
    
    doc.close()
    return text, local_text_chunks, local_images



def extract_raw_content(filepath: str, file_hash: str):
    doc = pymupdf.open(filepath)
    total_pages = len(doc)
    metadata_fallback = doc.metadata or {}
    doc.close() # Close handle before starting pool

    # Prepare arguments for the workers
    page_tasks = [(filepath, pnum, file_hash) for pnum in range(1, total_pages + 1)]
    
    raw_text_chunks = []
    raw_images = []
    first_pages_text_list = [None] * total_pages 

    # --- Parallel Execution ---
    # Using ProcessPoolExecutor to utilize all CPU cores for PDF rendering
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(process_single_page, page_tasks))

    # --- Reassemble Results ---
    for i, (text, chunks, images) in enumerate(results):
        page_num = i + 1
        
        # Collect first 5 pages for metadata
        if page_num <= 5:
            first_pages_text_list[i] = text
            
        raw_text_chunks.extend(chunks)
        raw_images.extend(images)

    first_pages_text = "\n".join(filter(None, first_pages_text_list))

    return raw_text_chunks, raw_images, first_pages_text, metadata_fallback



# === Main Ingestion ===
def ingest_documents(file_path: str, qdrant_url: str, qdrant_api_key: str, collection_name: str, verbose: bool = False):
    start_time = datetime.now()
    
    embedding_model = OpenAIEmbeddings()
    qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    # Setup Collection (Idempotent)
    if not qdrant_client.collection_exists(collection_name=collection_name):
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=embedding_model.dimensions, distance=models.Distance.COSINE)
        )
        
        # Create Indices only on creation to save time on subsequent runs
        for field in ["file_hash", "file_name", "type"]:
            qdrant_client.create_payload_index(collection_name, field, models.PayloadSchemaType.KEYWORD)
        qdrant_client.create_payload_index(collection_name, "text", models.PayloadSchemaType.TEXT)

    file_hash = get_file_hash(file_path)
    filename = os.path.basename(file_path)

    # Check existence
    existing = qdrant_client.scroll(
        collection_name=collection_name,
        scroll_filter={"must": [{"key": "file_hash", "match": {"value": file_hash}}]},
        limit=1
    )
    if existing[0]:
        print(f"✔ Skipping (already indexed): {filename}")
        return

    print(f"→ Processing: {filename}")
    
    # 1. CPU Extraction
    t_start_extraction = time.time()
    text_chunks, raw_images, first_pages_text, pdf_meta = extract_raw_content(file_path, file_hash)
    storage = get_storage_provider()
    print(f"   ⏱️ [Phase 1] CPU Extraction: {time.time() - t_start_extraction:.2f}s")    
    
    # 2. Parallel Processing
    print(f"   > Processing {len(text_chunks)} chunks & {len(raw_images)} images...")
    t_start_parallel = time.time()
    
    doc_metadata_result = None
    processed_images = []
    summarized_chunks = [None] * len(text_chunks)
    
    # We use a ThreadPool for network calls
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        
        # A. Start Metadata (Fast Groq)
        future_meta = executor.submit(extract_metadata_fast, first_pages_text)
        
        # B. Start Text Summarization (Fast Groq)
        chunk_futures = {executor.submit(robust_summarize_text, txt): i for i, (txt, _) in enumerate(text_chunks)}
        # Use the 'instant' model to ensure text processing finishes 
        # long before the Vision (GPT-4o) tasks.
        # chunk_futures = {
        #     executor.submit(
        #         summarize_text, 
        #         txt, 
        #         provider='groq', 
        #         model='llama-3.1-8b-instant',
        #         template_name="document_chunk_summarization"
        #     ): i for i, (txt, _) in enumerate(text_chunks)
        # }
        
        # C. Start Image Processing (Hybrid Upload/Analyze)
        # We separate Upload and Analysis so they don't block each other
        upload_futures = [] 
        vision_futures = []
        
        for img in raw_images:
            # 1. Fire Upload Task
            upload_futures.append(executor.submit(storage.save_image, img["bytes"], img["filename"]))
            
            # 2. Fire Vision Task
            b64_str = base64.b64encode(img["bytes"]).decode('utf-8')
            # Using partial to keep context
            def analyze_wrapper(b64, cap, fname, pnum):
                return {
                    "filename": fname,
                    "description": describe_image_with_gpt4o(b64, cap),
                    "caption": cap,
                    "page_number": pnum
                }
            vision_futures.append(executor.submit(analyze_wrapper, b64_str, img["caption"], img["filename"], img["page_number"]))

        # -- Collect Results --
        
        # 1. Metadata
        try:
            doc_metadata_result = future_meta.result()
        except Exception as e:
            print(f"   ! Metadata failed: {e}")
            doc_metadata_result = AdditionalMetadata(title=pdf_meta.get("title", filename), publication_year="Unknown", summary="N/A")

        # 2. Chunks
        for f in as_completed(chunk_futures):
            try: summarized_chunks[chunk_futures[f]] = f.result()
            except: summarized_chunks[chunk_futures[f]] = ""

        # 🔥 NEW: Start Embedding Text Chunks immediately while Vision is still running
        # This overlaps the ~2.5s embedding time with the remaining Vision time.
        base_info = f"Title: {doc_metadata_result.title}\nAuthors: {', '.join(doc_metadata_result.authors)}\n"
        embed_inputs = []
        points = []

        for (txt, pnum), summary in zip(text_chunks, summarized_chunks):
            content = f"{base_info}Summary: {summary}\nContent: {txt}"
            embed_inputs.append(content)
            points.append({"payload": {"type": "chunk", "text": content, "page_number": str(pnum), "summary": summary, "image_path": None}})
        
        # Add Doc Summary to initial batch
        final_sum = f"{base_info}Full Summary: {doc_metadata_result.summary}"
        embed_inputs.append(final_sum)
        points.append({"payload": {"type": "summary", "text": final_sum, "page_number": "0", "summary": "FULL_DOC", "image_path": None}})

        # Fire text embedding (Non-blocking if we use executor, but even sequential here 'hides' vision time)
        text_vectors = embedding_model.embed_documents(embed_inputs)

        # 3. Images (Vision) - Now we wait for the long pole
        for f in as_completed(vision_futures):
            try: processed_images.append(f.result())
            except Exception as e: print(f"   ! Vision failed: {e}")

        wait(upload_futures) 

        print(f"   ⏱️ [Phase 2] Parallel API calls (Vision/Meta/Summary): {time.time() - t_start_parallel:.2f}s")

        # 3. Batch Embedding (Now only for images)
        t_start_embed = time.time()
        print("   > Finalizing Embeddings...")
        
        image_embed_inputs = []
        image_points = []
        for img in processed_images:
            content = f"{base_info}Figure: {img['caption']}\nDescription: {img['description']}"
            image_embed_inputs.append(content)
            image_points.append({"payload": {"type": "figure", "text": content, "page_number": str(img['page_number']), "summary": "FIGURE", "image_path": img['filename']}})

        # Final small embedding call for images
        image_vectors = embedding_model.embed_documents(image_embed_inputs) if image_embed_inputs else []
        
        # Combine everything
        all_vectors = text_vectors + image_vectors
        all_points_metadata = points + image_points
        
        # Construct Qdrant Points
        qdrant_points = []
        common_payload = {
            "file_name": filename, "file_hash": file_hash, "file_title": doc_metadata_result.title,
            "authors": doc_metadata_result.authors, "keywords": doc_metadata_result.keywords, 
            "year": doc_metadata_result.publication_year, "creation_date": datetime.now().isoformat()
        }

        for i, pt in enumerate(all_points_metadata):
            qdrant_points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=all_vectors[i],
                payload={**common_payload, **pt["payload"]}
            ))

        qdrant_client.upsert(collection_name=collection_name, points=qdrant_points)
        print(f"   ⏱️ [Phase 3] Embedding & Qdrant Upsert: {time.time() - t_start_embed:.2f}s")

    #     # 3. Images (Vision)
    #     for f in as_completed(vision_futures):
    #         try: processed_images.append(f.result())
    #         except Exception as e: print(f"   ! Vision failed: {e}")

    #     # 4. Ensure Uploads Finished (Non-blocking usually, but we need to ensure success before DB entry)
    #     # We wait for uploads at the very end while the CPU is preparing the vectors, effectively hiding the latency
    #     wait(upload_futures) 

    # print(f"   ⏱️ [Phase 2] Parallel API calls (Vision/Meta/Summary): {time.time() - t_start_parallel:.2f}s")

    # # 3. Batch Embedding
    # t_start_embed = time.time()
    # print("   > Embedding...")
    
    # base_info = f"Title: {doc_metadata_result.title}\nAuthors: {', '.join(doc_metadata_result.authors)}\n"
    # embed_inputs = []
    # points = []

    # # Prepare Texts
    # for (txt, pnum), summary in zip(text_chunks, summarized_chunks):
    #     content = f"{base_info}Summary: {summary}\nContent: {txt}"
    #     embed_inputs.append(content)
    #     points.append({
    #         "payload": {"type": "chunk", "text": content, "page_number": str(pnum), "summary": summary, "image_path": None}
    #     })

    # for img in processed_images:
    #     content = f"{base_info}Figure: {img['caption']}\nDescription: {img['description']}"
    #     embed_inputs.append(content)
    #     points.append({
    #         "payload": {"type": "figure", "text": content, "page_number": str(img['page_number']), "summary": "FIGURE", "image_path": img['filename']}
    #     })
        
    # # Doc Summary
    # final_sum = f"{base_info}Full Summary: {doc_metadata_result.summary}"
    # embed_inputs.append(final_sum)
    # points.append({"payload": {"type": "summary", "text": final_sum, "page_number": "0", "summary": "FULL_DOC", "image_path": None}})

    # # Call API
    # vectors = embedding_model.embed_documents(embed_inputs)
    
    # # Construct Qdrant Points
    # qdrant_points = []
    # common_payload = {
    #     "file_name": filename, "file_hash": file_hash, "file_title": doc_metadata_result.title,
    #     "authors": doc_metadata_result.authors, "keywords": doc_metadata_result.keywords, 
    #     "year": doc_metadata_result.publication_year, "creation_date": datetime.now().isoformat()
    # }

    # for i, pt in enumerate(points):
    #     qdrant_points.append(PointStruct(
    #         id=str(uuid.uuid4()),
    #         vector=vectors[i],
    #         payload={**common_payload, **pt["payload"]}
    #     ))

    # qdrant_client.upsert(collection_name=collection_name, points=qdrant_points)
    # print(f"   ⏱️ [Phase 3] Embedding & Qdrant Upsert: {time.time() - t_start_embed:.2f}s")
    
    print(f"✅ Indexed {filename} in {(datetime.now() - start_time).total_seconds():.2f}s")