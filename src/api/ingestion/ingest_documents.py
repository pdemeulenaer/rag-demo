
#src/api/ingestion/ingest_documents.py
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
from threading import Semaphore

from src.api.core.config import config
from src.api.rag.summarize import summarize_text
from src.api.rag.utils.utils import prompt_template_config
from src.api.core.storage import get_storage_provider
from src.api.ingestion.common import build_point_payload


# === Config ===
# Limit concurrent calls to Groq/OpenAI to 15 (safe for most tiers)
# This is independent of MAX_WORKERS (which might be 40 for CPU tasks)
API_SEMAPHORE = Semaphore(15)
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

def rate_limited_summarize(text, model):
    """Acquires a 'ticket' from the semaphore before calling the API."""
    with API_SEMAPHORE:
        # This blocks until a slot is available
        return summarize_text(
            text, 
            provider='groq', 
            model=model, # e.g. 'llama-3.1-8b-instant'
            template_name="document_chunk_summarization"
        )

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
    """Sends image to LLM for description using YAML templates."""

    # 1. Load the template
    template = prompt_template_config(
        config.IMAGE_DESCRIPTION_PROMPT_TEMPLATE_PATH, 
        "image_description_generation"
    )

    # 2. Render the prompts with variables
    system_prompt = template["system"].render()
    user_prompt = template["user"].render(caption=caption)    

    # 3. Format messages for OpenAI
    # Note: Vision models accept text + image_url objects in the USER message
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {
                    "type": "image_url", 
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}", 
                        "detail": "high"
                    }
                },
            ],
        }
    ]

    # 4. API Call
    response = client.chat.completions.create(
        model=config.IMAGE_DESCRIPTION_MODEL,
        messages=messages,
        max_tokens=300
    )    

    # prompt = (
    #     "You are a scientific research assistant. Analyze this figure.\n"
    #     f"Caption: \"{caption}\"\n\n"
    #     "1. Identify figure type.\n"
    #     "2. Describe data trends/relationships.\n"
    #     "3. Summarize key insight.\n"
    #     "Provide a dense, searchable description."
    # )
    # # Use gpt-4o-mini if cost/speed is a priority, otherwise gpt-4o
    # response = client.chat.completions.create(
    #     model="gpt-4.1-mini", #"gpt-4o-mini", #"gpt-4o", 
    #     messages=[
    #         {
    #             "role": "user",
    #             "content": [
    #                 {"type": "text", "text": prompt},
    #                 {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}", "detail": "high"}},
    #             ],
    #         }
    #     ],
    #     max_tokens=300
    # )
    return response.choices[0].message.content

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

# def identify_figures_on_page(page) -> List[Dict[str, Any]]:
#     text_blocks = page.get_text("blocks")
#     # Pattern to catch the start of a caption
#     fig_pattern = re.compile(r"^\s*(?:Fig\.?|Figure|Scheme|Chart|Panel|Box)\s*\d*", re.IGNORECASE)
#     captions = []
    
#     # 1. Find captions
#     for i, block in enumerate(text_blocks):
#         block_text = block[4].strip()
#         # We only treat it as a caption if the block STARTS with the Figure label
#         # This ignores paragraphs that just mention "As seen in Fig 1..." in the middle
#         if fig_pattern.match(block_text):
#             cap_rect = pymupdf.Rect(block[:4])
#             cap_text = block_text.replace("\n", " ")
            
#             # Look ahead to see if the caption continues in the next block
#             for j in range(i + 1, len(text_blocks)):
#                 next_block = text_blocks[j]
#                 if (next_block[1] - cap_rect.y1) < 15 and abs(next_block[0] - cap_rect.x0) < 20:
#                     cap_rect |= pymupdf.Rect(next_block[:4])
#                     cap_text += " " + next_block[4].strip().replace("\n", " ")
#                 else: break
#             captions.append({"rect": cap_rect, "text": cap_text})

#     # Pre-fetch page objects for speed
#     image_info = page.get_image_info() 
#     drawings = page.get_drawings()      

#     # 2. Find figures based on captions
#     figures = []
#     for cap in captions:
#         search_bottom = cap["rect"].y0
#         search_top = 0
        
#         # Search upwards for the boundary of the figure
#         for block in reversed(text_blocks):
#             block_rect = pymupdf.Rect(block[:4])
#             if block_rect.y1 < search_bottom - 15:
#                 # If we hit a block with significant text, that's our top boundary
#                 if len(block[4].strip()) > 100: 
#                     search_top = block_rect.y1 + 2
#                     break
        
#         figure_rect = pymupdf.Rect(page.rect.x0, search_top, page.rect.x1, cap["rect"].y1)
#         figure_rect = (figure_rect + (-2, -2, 2, 2)) & page.rect

#         # --- REFINED OBJECT VERIFICATION ---
        
#         # A. Bitmap Check
#         has_image = any(figure_rect.intersects(pymupdf.Rect(img["bbox"])) for img in image_info)
        
#         # B. Drawing Check (Ignore tiny lines/noise)
#         # Scientific plots often use vector drawings
#         has_drawing = any(
#             figure_rect.intersects(pymupdf.Rect(d["rect"])) 
#             for d in drawings if d["rect"].width > 40 or d["rect"].height > 40
#         )

#         # C. Text Density Check (The Paragraph Killer)
#         # Paragraphs are dense (~25+ chars per 1k pts). Figures are airy (< 10).
#         text_inside = page.get_text("text", clip=figure_rect).strip()
#         area = figure_rect.width * figure_rect.height
#         density = (len(text_inside) / area * 1000) if area > 0 else 0

#         # Logic: Must have a visual object AND not be a wall of text
#         if (has_image or has_drawing) and density < 12:
#             figures.append({"rect": figure_rect, "caption": cap["text"]})
            
#     return figures
def identify_figures_on_page(page) -> List[Dict[str, Any]]:
    text_blocks = page.get_text("blocks")
    fig_pattern = re.compile(r"^\s*(?:Fig\.?|Figure|Scheme|Chart|Panel|Box)\s*\d*", re.IGNORECASE)
    captions = []
    
    # 1. Detect Caption Blocks
    for i, block in enumerate(text_blocks):
        block_text = block[4].strip()
        if fig_pattern.match(block_text):
            cap_rect = pymupdf.Rect(block[:4])
            cap_text = block_text.replace("\n", " ")
            
            # Merge multi-line captions
            for j in range(i + 1, len(text_blocks)):
                next_block = text_blocks[j]
                if (next_block[1] - cap_rect.y1) < 20 and abs(next_block[0] - cap_rect.x0) < 50:
                    cap_rect |= pymupdf.Rect(next_block[:4])
                    cap_text += " " + next_block[4].strip().replace("\n", " ")
                else: break
            captions.append({"rect": cap_rect, "text": cap_text})

    image_info = page.get_image_info() 
    drawings = page.get_drawings()      

    figures = []
    for cap in captions:
        cap_rect = cap["rect"]
        
        # 2. Dynamic Search Zone (Expanded Horizon)
        # We find the "Barrier" (previous paragraph) as before
        search_top = 0
        for block in text_blocks:
            b_rect = pymupdf.Rect(block[:4])
            if b_rect.y1 < cap_rect.y0 - 5:
                text = block[4].strip()
                if fig_pattern.match(text) or len(text) > 100:
                    if b_rect.y1 > search_top: search_top = b_rect.y1
        
        # EXTENDED HORIZON: 
        # Search from the barrier down to the BOTTOM of the caption.
        # This captures multi-panel plots even if the caption is off to the side.
        search_rect = pymupdf.Rect(0, search_top, page.rect.width, cap_rect.y1 + 10)
        
        candidates = []

        # 3. Find Visuals (Images & Drawings)
        for img in image_info:
            bbox = pymupdf.Rect(img["bbox"])
            if bbox.intersects(search_rect):
                candidates.append(bbox)

        for d in drawings:
            d_rect = pymupdf.Rect(d["rect"])
            # Ignore thin decorative lines or page borders
            if d_rect.width < 15 or d_rect.height < 15: continue
            if d_rect.intersects(search_rect):
                candidates.append(d_rect)

        # 4. Construct Figure
        if candidates:
            # Union of all visual parts
            visual_rect = candidates[0]
            for c in candidates[1:]:
                visual_rect |= c
            
            # Final bounding box: All visuals + the caption itself
            final_rect = visual_rect | cap_rect

            # Padding and bounds check
            final_rect = (final_rect + (-5, -5, 5, 5)) & page.rect
            
            # 5. Density Check
            # We check density on the visual_rect only. 
            # Multi-panel figures have a lot of white space, so density is usually very low (< 5).
            text_inside = page.get_text("text", clip=visual_rect).strip()
            area = visual_rect.width * visual_rect.height
            density = (len(text_inside) / area * 1000) if area > 0 else 0
            
            if final_rect.width > 50 and final_rect.height > 50 and density < 20:
                figures.append({"rect": final_rect, "caption": cap["text"]})
            
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


# def process_single_page(page_data):
#     """Worker function to process one page at a time."""
#     # Unpack data
#     filepath, page_number, file_hash = page_data
    
#     # We must open a new doc handle per process/thread for safety
#     doc = pymupdf.open(filepath)
#     page = doc[page_number - 1] # 0-indexed
    
#     local_text_chunks = []
#     local_images = []
    
#     text = page.get_text()
    
#     # 1. Chunking logic (Matches your current per-page style)
#     if text.strip():
#         chunks = get_text_chunks_recursive(text)
#         for chunk in chunks:
#             local_text_chunks.append((chunk, page_number))

#     # 2. Figure detection
#     figures = identify_figures_on_page(page)
#     for i, fig in enumerate(figures):
#         match = re.search(r"(?:Fig(?:\.|ure)?)\s*(\d+)", fig["caption"], re.IGNORECASE)
#         fig_label = match.group(1) if match else f"p{page_number}_{i}"

#         try:
#             pix = page.get_pixmap(clip=fig["rect"], dpi=150, colorspace=fitz.csRGB, alpha=False)
#             if pix.width < 100 or pix.height < 100: continue
            
#             img_bytes = pix.tobytes(output="jpg", jpg_quality=80) 
#             filename = f"{file_hash}_fig_{fig_label}.jpg"
            
#             local_images.append({
#                 "bytes": img_bytes,
#                 "filename": filename,
#                 "caption": fig["caption"],
#                 "page_number": page_number
#             })
#         except Exception: pass
    
#     doc.close()
#     return text, local_text_chunks, local_images
def process_single_page(page_data):
    """Worker function to process one page at a time."""
    filepath, page_number, file_hash = page_data
    
    doc = pymupdf.open(filepath)
    page = doc[page_number - 1] 
    
    local_text_chunks = []
    local_images = []
    
    text = page.get_text()
    
    # 1. Chunking logic
    if text.strip():
        chunks = get_text_chunks_recursive(text)
        for chunk in chunks:
            local_text_chunks.append((chunk, page_number))

    # 2. Figure detection
    figures = identify_figures_on_page(page)
    for i, fig in enumerate(figures):
        # IMPROVED REGEX: Captures "1.1", "2-3", "A.1" etc. 
        match = re.search(r"(?:Fig(?:\.|ure)?)\s*([\d\.\-A-Za-z]+)", fig["caption"], re.IGNORECASE)
        
        if match:
            # Clean the label (replace dots with underscores for filename safety)
            fig_label = re.sub(r"[^a-zA-Z0-9]", "_", match.group(1))
        else:
            fig_label = f"unlabeled_{i}"

        try:

            # --- Text Density Filter ---
            # 1. Get the text within the block
            text_inside_fig = page.get_text("text", clip=fig["rect"]).strip()
            
            # 2. Check the area of the detected figure
            # Width x Height in points
            rect_area = fig["rect"].width * fig["rect"].height
            
            # 3. Calculate "Character Density" 
            # (Chars per 1000 square points)
            char_density = (len(text_inside_fig) / rect_area) * 1000 if rect_area > 0 else 0

            # 4. Filter Logic:
            # Standard paragraphs (like the one in your screenshot) have high density (~15-30+)
            # Scientific figures with labels/captions usually stay below 10.
            if char_density > 12: 
                # If density is high, check if it's just a long caption 
                # or a real paragraph by seeing if it has standard sentence structure
                if len(text_inside_fig.split()) > 40: # Likely a text paragraph
                    continue

            # --- Proceed with Extraction if it passed the density test ---
            pix = page.get_pixmap(clip=fig["rect"], dpi=150, colorspace=fitz.csRGB, alpha=False)
            
            # Increased filter: 100px is often too small for PhD theses (captures logos/icons)
            # 150px helps ignore small decorative elements.
            if pix.width < 150 or pix.height < 150: continue
            
            img_bytes = pix.tobytes(output="jpg", jpg_quality=80) 
            
            # COLLISION-PROOF FILENAME: hash + page_number + unique_index + label
            # This prevents Figure 1.1 on page 5 from overwriting Figure 1.1 on page 50.
            filename = f"{file_hash}_p{page_number}_idx{i}_{fig_label}.jpg"
            
            local_images.append({
                "bytes": img_bytes,
                "filename": filename,
                "caption": fig["caption"],
                "page_number": page_number
            })
        except Exception: pass
    
    doc.close()
    return text, local_text_chunks, local_images



# def extract_raw_content(filepath: str, file_hash: str):
#     doc = pymupdf.open(filepath)
#     total_pages = len(doc)
#     metadata_fallback = doc.metadata or {}
#     doc.close() # Close handle before starting pool

#     # Prepare arguments for the workers
#     page_tasks = [(filepath, pnum, file_hash) for pnum in range(1, total_pages + 1)]
    
#     raw_text_chunks = []
#     raw_images = []
#     first_pages_text_list = [None] * total_pages 

#     # --- Parallel Execution ---
#     # Using ProcessPoolExecutor to utilize all CPU cores for PDF rendering
#     with ProcessPoolExecutor() as executor:
#         results = list(executor.map(process_single_page, page_tasks))

#     # --- Reassemble Results ---
#     for i, (text, chunks, images) in enumerate(results):
#         page_num = i + 1
        
#         # Collect first 5 pages for metadata
#         if page_num <= 5:
#             first_pages_text_list[i] = text
            
#         raw_text_chunks.extend(chunks)
#         raw_images.extend(images)

#     first_pages_text = "\n".join(filter(None, first_pages_text_list))

#     return raw_text_chunks, raw_images, first_pages_text, metadata_fallback
def extract_raw_content(filepath: str, file_hash: str):
    doc = pymupdf.open(filepath)
    total_pages = len(doc)
    metadata_fallback = doc.metadata or {}
    doc.close() 

    # Prepare arguments
    page_tasks = [(filepath, pnum, file_hash) for pnum in range(1, total_pages + 1)]
    
    # --- Parallel Execution ---
    with ProcessPoolExecutor() as executor:
        # map() preserves order, so results[0] is page 1
        results = list(executor.map(process_single_page, page_tasks))

    raw_text_chunks = []
    raw_images = []
    first_pages_text_list = [None] * min(5, total_pages) 

    # --- Reassemble Results ---
    for i, (text, chunks, images) in enumerate(results):
        page_num = i + 1
        
        if page_num <= 5:
            first_pages_text_list[page_num-1] = text
            
        raw_text_chunks.extend(chunks)
        raw_images.extend(images)

    first_pages_text = "\n".join(filter(None, first_pages_text_list))

    return raw_text_chunks, raw_images, first_pages_text, metadata_fallback



# === Main Ingestion ===
def ingest_documents(file_path: str, verbose: bool = False):
    start_time = datetime.now()
    
    # --- Setup ---
    embedding_model = OpenAIEmbeddings()
    qdrant_client = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY)
    
    # 1. Rate Limiter: Limit concurrent Groq/OpenAI calls to 15 to prevent 429 Errors
    api_semaphore = Semaphore(15)

    def rate_limited_summarize(text):
        with api_semaphore:
            # Use the instant model for speed
            return summarize_text(text, provider='groq', model='llama-3.1-8b-instant', template_name="document_chunk_summarization")

    # --- Collection Check (Idempotent) ---
    if not qdrant_client.collection_exists(collection_name=config.QDRANT_COLLECTION_NAME):
        qdrant_client.create_collection(
            collection_name=config.QDRANT_COLLECTION_NAME,
            vectors_config=models.VectorParams(size=embedding_model.dimensions, distance=models.Distance.COSINE)
        )
        for field in ["file_hash", "file_name", "type"]:
            qdrant_client.create_payload_index(config.QDRANT_COLLECTION_NAME, field, models.PayloadSchemaType.KEYWORD)
        qdrant_client.create_payload_index(config.QDRANT_COLLECTION_NAME, "text", models.PayloadSchemaType.TEXT)

    file_hash = get_file_hash(file_path)
    filename = os.path.basename(file_path)

    existing = qdrant_client.scroll(
        collection_name=config.QDRANT_COLLECTION_NAME,
        scroll_filter={"must": [{"key": "file_hash", "match": {"value": file_hash}}]},
        limit=1
    )
    if existing[0]:
        print(f"✔ Skipping (already indexed): {filename}")
        return

    print(f"→ Processing: {filename}")
    
    # --- Phase 1: CPU Extraction ---
    t_start_extraction = time.time()
    text_chunks, raw_images, first_pages_text, pdf_meta = extract_raw_content(file_path, file_hash)
    storage = get_storage_provider()
    print(f"   ⏱️ [Phase 1] CPU Extraction: {time.time() - t_start_extraction:.2f}s")    
    
    # --- Phase 2: Parallel Processing (Pipelined) ---
    print(f"   > Processing {len(text_chunks)} chunks & {len(raw_images)} images...")
    t_start_parallel = time.time()
    
    doc_metadata_result = None
    processed_images = []
    summarized_chunks = [None] * len(text_chunks)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        
        # A. Metadata
        future_meta = executor.submit(extract_metadata_fast, first_pages_text)
        
        # B. Text Summarization (With Rate Limiting)
        chunk_futures = {
            executor.submit(rate_limited_summarize, txt): i 
            for i, (txt, _) in enumerate(text_chunks)
        }
        
        # C. Vision (Hybrid Upload/Analyze)
        upload_futures = [] 
        vision_futures = []
        
        for img in raw_images:
            upload_futures.append(executor.submit(storage.save_image, img["bytes"], img["filename"]))
            
            b64_str = base64.b64encode(img["bytes"]).decode('utf-8')
            def analyze_wrapper(b64, cap, fname, pnum):
                return {
                    "filename": fname,
                    "description": describe_image_with_gpt4o(b64, cap),
                    "caption": cap,
                    "page_number": pnum
                }
            vision_futures.append(executor.submit(analyze_wrapper, b64_str, img["caption"], img["filename"], img["page_number"]))

        # -- Collect Text Results First --
        try:
            doc_metadata_result = future_meta.result()
        except Exception:
            doc_metadata_result = AdditionalMetadata(title=filename, publication_year="Unknown", summary="N/A", authors=[])

        for f in as_completed(chunk_futures):
            try: summarized_chunks[chunk_futures[f]] = f.result().summary # Check if your function returns obj or str
            except: summarized_chunks[chunk_futures[f]] = ""

        # 🔥 PIPELINE OPTIMIZATION: Embed text immediately while images are still processing
        base_info = f"Title: {doc_metadata_result.title}\nAuthors: {', '.join(doc_metadata_result.authors)}\n"
        embed_inputs = []
        points_metadata = []

        # Prepare Text Payloads
        for (txt, pnum), summary in zip(text_chunks, summarized_chunks):
            content = f"{base_info}Summary: {summary}\nContent: {txt}"
            embed_inputs.append(content)
            # points_metadata.append({"payload": {"type": "chunk", "text": content, "page_number": str(pnum), "summary": summary, "image_path": None}})

            payload = build_point_payload(
                file_name=filename,
                file_hash=file_hash,
                doc_meta=doc_metadata_result,
                text=content,
                point_type="chunk",
                img_page=pnum,                 # page number of this chunk
            )

            # The helper does not know about the per‑chunk summary, so we add it manually.
            payload["summary"] = summary
            payload["page_number"] = str(pnum)   # keep the legacy key that the rest of the code expects

            points_metadata.append({"payload": payload})           
        
        # Add Doc Summary
        final_sum = f"{base_info}Full Summary: {doc_metadata_result.summary}"
        embed_inputs.append(final_sum)
        # points_metadata.append({"payload": {"type": "summary", "text": final_sum, "page_number": "0", "summary": "FULL_DOC", "image_path": None}})

        summary_payload = build_point_payload(
            file_name=filename,
            file_hash=file_hash,
            doc_meta=doc_metadata_result,
            text=final_sum,
            point_type="summary",
        )

        # Keep the legacy keys that downstream code may read.
        summary_payload["page_number"] = "0"
        summary_payload["summary"] = "FULL_DOC"
        summary_payload["image_path"] = None

        points_metadata.append({"payload": summary_payload})        

        # Fire Text Embedding (Hides Latency)
        text_vectors = embedding_model.embed_documents(embed_inputs) if embed_inputs else []

        # -- Collect Vision Results (The Long Pole) --
        for f in as_completed(vision_futures):
            try: processed_images.append(f.result())
            except Exception: pass

        wait(upload_futures) 

    print(f"   ⏱️ [Phase 2] Parallel API calls: {time.time() - t_start_parallel:.2f}s")

    # --- Phase 3: Finalize Embeddings & Batch Upsert ---
    t_start_embed = time.time()
    
    # Embed Images
    image_embed_inputs = []
    image_points_metadata = []
    for img in processed_images:
        content = f"{base_info}Figure: {img['caption']}\nDescription: {img['description']}"
        image_embed_inputs.append(content)
        # image_points_metadata.append({"payload": {"type": "figure", "text": content, "page_number": str(img['page_number']), "summary": "FIGURE", "image_path": img['filename']}})

        figure_payload = build_point_payload(
            file_name=filename,
            file_hash=file_hash,
            doc_meta=doc_metadata_result,
            text=content,
            point_type="figure",
            img_caption=img["caption"],
            img_page=img["page_number"],
            img_path=img["filename"],
        )

        # Preserve the legacy “summary” field that the old code stored.
        figure_payload["summary"] = "FIGURE"

        image_points_metadata.append({"payload": figure_payload})        

    image_vectors = embedding_model.embed_documents(image_embed_inputs) if image_embed_inputs else []
    
    # Merge All Data
    all_vectors = text_vectors + image_vectors
    all_metas = points_metadata + image_points_metadata
    
    # Batch Upsert to Qdrant (Safe for large files)
    print(f"   > Upserting {len(all_vectors)} vectors in batches...")
    
    common_payload = {
        "file_name": filename, "file_hash": file_hash, "file_title": doc_metadata_result.title,
        "authors": doc_metadata_result.authors, "keywords": doc_metadata_result.keywords, 
        "year": doc_metadata_result.publication_year, "creation_date": datetime.now().isoformat()
    }
    
    BATCH_SIZE = 50
    zip_data = list(zip(all_vectors, all_metas))
    
    for i in range(0, len(zip_data), BATCH_SIZE):
        batch = zip_data[i : i + BATCH_SIZE]
        points_batch = []
        for vector, meta in batch:
            points_batch.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={**common_payload, **meta["payload"]}
            ))
        try:
            qdrant_client.upsert(collection_name=config.QDRANT_COLLECTION_NAME, points=points_batch)
        except Exception as e:
            print(f"     ! Batch failed: {e}")

    print(f"   ⏱️ [Phase 3] Embedding & Batch Upsert: {time.time() - t_start_embed:.2f}s")
    print(f"✅ Indexed {filename} in {(datetime.now() - start_time).total_seconds():.2f}s")