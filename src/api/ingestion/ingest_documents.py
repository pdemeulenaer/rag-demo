# src/api/ingestion/ingest_documents.py

import os
import hashlib
import uuid
import json
import pymupdf
import re
import base64
import statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict, Any

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from langchain.text_splitter import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance, PayloadSchemaType
from langchain.embeddings.base import Embeddings
from openai import OpenAI, RateLimitError, APIError
import instructor
from pydantic import BaseModel, Field
import concurrent.futures
from qdrant_client.http import models

from src.api.core.config import config
from src.api.rag.summarize import summarize_text
from src.api.rag.utils.utils import prompt_template_config
from src.api.core.storage import get_storage_provider


# === Config ===
# Define max workers for parallel API calls (prevent hitting rate limits too hard)
MAX_WORKERS = 10 

client = OpenAI(api_key=config.OPENAI_API_KEY)
openai_client = instructor.from_openai(client)

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
    """Structured metadata extracted from a scientific PDF."""
    title: str = Field(..., description="The title of the document")
    authors: list[str] = Field(default_factory=list, description="List of authors of the document, as a string")
    keywords: list[str] = Field(default_factory=list, description="List of keywords (empty if none)")
    publication_year: str = Field(..., description="The correct year of publication, found directly in the text (e.g., '2023').") 
    summary: str = Field(..., description="The abstract or summary of the document, if present. If not present, generate an extensive, detailed summary from the provided text.")


# === 1. Robust API Calls with Retries ===
# We wrap LLM calls with tenacity to handle 429 Rate Limits automatically
@retry(
    retry=retry_if_exception_type((RateLimitError, APIError)),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    stop=stop_after_attempt(5)
)
def describe_image_with_gpt4o(base64_image: str, caption: str = "") -> str:
    """Sends image to GPT-4o for description."""
    prompt = (
        "You are a scientific research assistant. Analyze this figure extracted from a research paper.\n"
        f"Context/Caption: \"{caption}\"\n\n"
        "1. Identify the type of figure (chart, diagram, microscopy, etc.).\n"
        "2. Describe axes, data trends, and error bars if applicable.\n"
        "3. If it has multiple panels (A, B, C...), describe the relationship between them.\n"
        "4. Summarize the key scientific insight.\n"
        "Provide a dense, searchable description."
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high" # Essential for reading scientific labels
                        },
                    },
                ],
            }
        ],
        max_tokens=600
    )
    return response.choices[0].message.content

@retry(
    retry=retry_if_exception_type((RateLimitError, APIError)),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    stop=stop_after_attempt(5)
)
def extract_metadata_with_llm(text: str) -> AdditionalMetadata:
    prompt_template = prompt_template_config(config.RAG_PROMPT_TEMPLATE_PATH, "rag_ingestion")
    system_prompt = prompt_template["system"].render()
    user_prompt = prompt_template["user"].render(
        input_text=text,
        output_json_schema=json.dumps(OUTPUT_SCHEMA, indent=2)
    )

    # OpenAI call with response_model for structured output
    chat = openai_client.chat.completions.create(
        model=config.METADATA_MODEL,
        response_model=AdditionalMetadata,  # ✅ Instructor enforces this
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=config.METADATA_MODEL_TEMPERATURE,
        max_tokens=config.METADATA_MODEL_MAX_TOKENS
    )    

    # # Groq call with response_model for structured output    
    # chat = groq_client.chat.completions.create(
    #     model=config.METADATA_MODEL,
    #     response_model=AdditionalMetadata,  # ✅ Instructor enforces this
    #     messages=[
    #         {"role": "system", "content": system_prompt},
    #         {"role": "user", "content": user_prompt},
    #     ],
    #     temperature=config.METADATA_MODEL_TEMPERATURE,
    #     max_tokens=config.METADATA_MODEL_MAX_TOKENS
    # )    

    return chat

@retry(
    retry=retry_if_exception_type((RateLimitError, APIError)),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    stop=stop_after_attempt(3)
)
def robust_summarize_text(text: str) -> str:
    """Wrapper for your existing summarize_text to make it retry-safe."""
    # Importing here to avoid circular dependency issues if any
    summary_obj = summarize_text(
        text, provider='groq', model=config.SUMMARIZATION_MODEL,
        temperature=config.SUMMARIZATION_MODEL_TEMPERATURE, 
        max_tokens=config.SUMMARIZATION_MODEL_MAX_TOKENS,
        template_name="document_chunk_summarization"
    )
    return summary_obj.summary.strip()

class OpenAIEmbeddings(Embeddings):
    """A wrapper for OpenAI's embedding model."""

    def __init__(self, model_name: str = "text-embedding-3-small"):
        self.model_name = model_name
        self.client = client
        self.dimensions = 1536  # text-embedding-3-small has a dimension of 1536 by default

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # OpenAI supports batch embedding.
        # Ensure we don't exceed max batch size (e.g., 2048).
        # Simple batching logic:
        batch_size = 100
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
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
        chunk_size=5000, # Increased chunk size for better context
        chunk_overlap=500,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    return splitter.split_text(text)

def identify_figures_on_page(page) -> List[Dict[str, Any]]:
    # 1. Get Caption Blocks (The most reliable anchor)
    text_blocks = page.get_text("blocks")
    fig_pattern = re.compile(r"^\s*(?:Fig\.?|Figure|Scheme|Chart|Panel|Box)\s*\d*", re.IGNORECASE)
    captions = []
    for i, block in enumerate(text_blocks):
        if fig_pattern.match(block[4]):
            cap_rect = pymupdf.Rect(block[:4])
            cap_text = block[4].strip().replace("\n", " ")
            # Merge subsequent lines if they are part of the same paragraph
            for j in range(i + 1, len(text_blocks)):
                next_block = text_blocks[j]
                if (next_block[1] - cap_rect.y1) < 15 and abs(next_block[0] - cap_rect.x0) < 20:
                    cap_rect |= pymupdf.Rect(next_block[:4])
                    cap_text += " " + next_block[4].strip().replace("\n", " ")
                else: break
            captions.append({"rect": cap_rect, "text": cap_text})

    # 2. Identify "Figure Zone" by searching UP from the caption
    figures = []
    for cap in captions:
        # Define search area: full page width, from top of page down to the caption
        search_top = 0
        search_bottom = cap["rect"].y0
        
        # Refine search_top: Look for the nearest text block ABOVE that isn't a sub-panel label
        # This helps avoid capturing the previous paragraph.
        for block in reversed(text_blocks):
            block_rect = pymupdf.Rect(block[:4])
            # If block is above the caption and likely body text (long text)
            if block_rect.y1 < search_bottom - 20:
                # Stop searching up if we hit a text block that looks like body text
                if len(block[4].strip()) > 100: 
                    search_top = block_rect.y1 + 5
                    break
        
        # Create final crop area: The space between the previous paragraph and the caption
        figure_rect = pymupdf.Rect(page.rect.x0, search_top, page.rect.x1, cap["rect"].y1)
        # Add a bit of padding and clip to page
        figure_rect = (figure_rect + (-5, -5, 5, 5)) & page.rect
        figures.append({"rect": figure_rect, "caption": cap["text"]})
    return figures


# === 2. Refactored Extraction Phase (Pure CPU/Disk) ===
def extract_raw_content(filepath: str, file_hash: str):
    """
    Step 1: Extract all raw data (text & image bytes) WITHOUT calling any external APIs.
    """
    doc = pymupdf.open(filepath)
    raw_text_chunks = [] # List of (text, page_number)
    raw_images = []      # List of dicts with bytes, caption, etc.
    first_pages_text = ""
    
    metadata_fallback = doc.metadata or {}
    fallback_fig_counter = 1

    for page_number, page in enumerate(doc, start=1):
        # Text
        text = page.get_text()
        if page_number <= 10:
            first_pages_text += "\n" + text
        
        if text.strip():
            chunks = get_text_chunks_recursive(text)
            for chunk in chunks:
                raw_text_chunks.append((chunk, page_number))

        # Images
        figures = identify_figures_on_page(page)
        for fig in figures:
            match = re.search(r"(?:Fig(?:\.|ure)?)\s*(\d+)", fig["caption"], re.IGNORECASE)
            if match:
                fig_label = match.group(1)
            else:
                fig_label = f"unlabeled_{fallback_fig_counter}"
                fallback_fig_counter += 1

            try:
                pix = page.get_pixmap(clip=fig["rect"], dpi=200)
                if pix.width < 100 or pix.height < 100: continue
                
                img_bytes = pix.tobytes("png")
                filename = f"{file_hash}_fig_{fig_label}.png"
                
                raw_images.append({
                    "bytes": img_bytes,
                    "filename": filename,
                    "caption": fig["caption"],
                    "page_number": page_number
                })
            except Exception as e:
                print(f"Error extracting figure on p{page_number}: {e}")

    return raw_text_chunks, raw_images, first_pages_text, metadata_fallback


# === 3. Main Ingestion Logic (Parallelized) ===
def ingest_documents(file_path: str, qdrant_url: str, qdrant_api_key: str, collection_name: str, verbose: bool = False):
    
    start_time = datetime.now()
    
    # -- Setup Qdrant --
    embedding_model = OpenAIEmbeddings()
    qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

# 1. Setup Collection and Indices
    if not qdrant_client.collection_exists(collection_name=collection_name):
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=embedding_model.dimensions, distance=models.Distance.COSINE)
        )

    # Metadata Indices
    for field in ["file_hash", "file_name", "file_title", "authors", "keywords", "page_number", "type", "image_path"]:
        qdrant_client.create_payload_index(
            collection_name=collection_name, 
            field_name=field, 
            field_schema=models.PayloadSchemaType.KEYWORD
        )

    # The Full-Text Index
    qdrant_client.create_payload_index(
        collection_name=collection_name, 
        field_name="text", 
        field_schema=models.PayloadSchemaType.TEXT
    )

    filename = os.path.basename(file_path)
    file_hash = get_file_hash(file_path)

    # Check existence
    existing = qdrant_client.scroll(
        collection_name=collection_name,
        scroll_filter={"must": [{"key": "file_hash", "match": {"value": file_hash}}]},
        limit=1
    )
    if existing[0]:
        print(f"✔ Skipping (already indexed): {filename}")
        return

    print(f"→ Starting Ingestion: {filename}")
    
    
    # -- 1. FAST Extraction (No API calls yet) --
    text_chunks, raw_images, first_pages_text, pdf_meta = extract_raw_content(file_path, file_hash)
    storage = get_storage_provider()
    
    # -- 2. PARALLEL Processing (The magic happens here) --
    # We will hold results here
    processed_images = [] # will hold {description, filename, ...}
    summarized_chunks = [None] * len(text_chunks) # preserve order
    doc_metadata_result = None

    print(f"   > Processing {len(text_chunks)} text chunks and {len(raw_images)} images in parallel...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        
        # A. Metadata Extraction Task
        future_meta = executor.submit(extract_metadata_with_llm, first_pages_text)
        
        # B. Image Tasks (Upload + Analyze)
        image_futures_map = {}
        for img in raw_images:
            def process_image(img_data):
                # 1. Upload to Storage (Network I/O)
                storage.save_image(img_data["bytes"], img_data["filename"])
                
                # 2. Analyze (Network I/O)
                b64_str = base64.b64encode(img_data["bytes"]).decode('utf-8')
                desc = describe_image_with_gpt4o(b64_str, img_data["caption"])
                
                return {
                    "filename": img_data["filename"],
                    "description": desc,
                    "caption": img_data["caption"],
                    "page_number": img_data["page_number"]
                }
            
            f = executor.submit(process_image, img)
            image_futures_map[f] = img["filename"]

        # C. Text Summarization Tasks
        chunk_futures_map = {}
        for i, (txt, _) in enumerate(text_chunks):
            f = executor.submit(robust_summarize_text, txt)
            chunk_futures_map[f] = i

        # -- Wait for Results --
        
        # 1. Get Metadata
        try:
            doc_metadata_result = future_meta.result()
        except Exception as e:
            print(f"   ! Metadata extraction failed: {e}")
            # Fallback
            doc_metadata_result = AdditionalMetadata(
                title=pdf_meta.get("title", filename),
                publication_year="Unknown",
                summary="Metadata extraction failed."
            )

        # 2. Get Images
        for f in as_completed(image_futures_map):
            try:
                res = f.result()
                processed_images.append(res)
            except Exception as e:
                fname = image_futures_map[f]
                print(f"   ! Failed to process image {fname}: {e}")

        # 3. Get Chunk Summaries
        for f in as_completed(chunk_futures_map):
            idx = chunk_futures_map[f]
            try:
                summarized_chunks[idx] = f.result()
            except Exception as e:
                print(f"   ! Chunk summary failed: {e}")
                summarized_chunks[idx] = ""

    # -- 3. Prepare Payloads for Batch Embedding --
    
    # Merge Metadata
    final_title = doc_metadata_result.title
    final_authors = doc_metadata_result.authors or to_list(pdf_meta.get("author"))
    final_year = doc_metadata_result.publication_year
    final_summary = doc_metadata_result.summary

    points_to_upsert = []
    
    # Prepare a list of text strings to embed in one go
    # Structure: (text_to_embed, payload_dict_template)
    embed_queue = []

    base_info = f"Title: {final_title}\nYear: {final_year}\nAuthors: {', '.join(final_authors)}\n"

    # A. Text Chunks
    for i, ((chunk_text, page_num), summary) in enumerate(zip(text_chunks, summarized_chunks)):
        text_for_vec = f"{base_info}Summary: {summary}\n\nContent: {chunk_text}"
        payload = {
            "type": "chunk",
            "text": text_for_vec, # Store the full context text or just raw chunk? Usually full context.
            "page_number": str(page_num),
            "summary": summary,
            "image_path": None
        }
        embed_queue.append((text_for_vec, payload))

    # B. Images
    for img in processed_images:
        text_for_vec = f"{base_info}Figure Caption: {img['caption']}\nDescription: {img['description']}"
        payload = {
            "type": "figure",
            "text": text_for_vec,
            "page_number": str(img['page_number']),
            "summary": "FIGURE",
            "image_path": img['filename'] # Just the filename!
        }
        embed_queue.append((text_for_vec, payload))

    # C. Document Summary
    doc_sum_text = f"{base_info}Full Document Summary: {final_summary}"
    embed_queue.append((doc_sum_text, {
        "type": "summary",
        "text": doc_sum_text,
        "page_number": "0",
        "summary": "FULL_DOC",
        "image_path": None
    }))

    # -- 4. Batch Embedding (One API Call) --
    if embed_queue:
        print("   > Generating embeddings...")
        texts = [x[0] for x in embed_queue]
        vectors = embedding_model.embed_documents(texts)
        
        # Zip back together
        for vec, (_, partial_payload) in zip(vectors, embed_queue):
            # Add common fields
            full_payload = {
                **partial_payload,
                "file_name": filename,
                "file_hash": file_hash,
                "file_title": final_title,
                "authors": final_authors,
                "keywords": doc_metadata_result.keywords,
                "year": final_year,
                "creation_date": datetime.now().isoformat()
            }
            
            points_to_upsert.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload=full_payload
            ))

        # -- 5. Upsert --
        qdrant_client.upsert(collection_name=collection_name, points=points_to_upsert)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"✅ Indexed {filename} with {len(points_to_upsert)} points in {elapsed:.2f}s")



# Create a simple custom exception for clarity
class IngestionError(Exception):
    pass    