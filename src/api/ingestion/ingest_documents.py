# src/api/ingestion/ingest_documents.py

import os
import httpx
import hashlib
import uuid
import json
import pymupdf
import re
import base64
import io
from PIL import Image
from datetime import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance, PayloadSchemaType
from typing import List, Tuple, Dict, Any
import statistics
from langchain.embeddings.base import Embeddings
from openai import OpenAI
import instructor
from pydantic import BaseModel, Field

from src.api.core.config import config
from src.api.rag.summarize import summarize_text
from src.api.rag.utils.utils import prompt_template_config, prompt_template_registry


# === Config ===
PDF_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/folder"))
# Folder for storing extracted images
IMAGES_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/images"))
os.makedirs(IMAGES_FOLDER, exist_ok=True)


# === OpenAI Embedding Class ===
client = OpenAI(api_key=config.OPENAI_API_KEY)
openai_client = instructor.from_openai(client) 
# Wrap OpenAI client with Instructor
# client = instructor.from_openai(OpenAI(api_key=OPENAI_API_KEY))
# groq_client = instructor.from_openai(
#     OpenAI(
#         base_url="https://api.groq.com/openai/v1",
#         api_key=config.GROQ_API_KEY
#     )
# )

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


# === Helper: Image Analysis ===
def describe_image_with_gpt4o(base64_image: str, caption: str = "") -> str:
    """Sends image to GPT-4o to get a detailed scientific description."""
    
    prompt = (
        "You are a scientific research assistant. Analyze this figure extracted from a research paper.\n"
        f"Context/Caption: \"{caption}\"\n\n"
        "1. Identify the type of figure (chart, diagram, microscopy, etc.).\n"
        "2. If it's a chart, describe axes, data trends, and error bars.\n"
        "3. If it has multiple panels (A, B, C...), describe the relationship between them.\n"
        "4. Summarize the key scientific insight provided by this figure.\n"
        "Provide a dense, searchable description."
    )

    response = client.chat.completions.create(
        model="gpt-4o",  # Best for vision
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


class OpenAIEmbeddings(Embeddings):
    """A wrapper for OpenAI's embedding model."""

    def __init__(self, model_name: str = "text-embedding-3-small"):
        self.model_name = model_name
        self.client = client
        self.dimensions = 1536  # text-embedding-3-small has a dimension of 1536 by default

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds a list of documents."""
        response = self.client.embeddings.create(
            input=texts,
            model=self.model_name,
        )
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> List[float]:
        """Embeds a single query string."""
        return self.embed_documents([text])[0]


# === File Hashing ===
def get_file_hash(filepath) -> str:
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# === Chunking ===
def get_text_chunks_recursive(text) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=10000,
        chunk_overlap=2000,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    return splitter.split_text(text)



# === New Logic: Figure Detection & Merging ===
def identify_figures_on_page(page) -> List[Dict[str, Any]]:
    """
    Scans a PDF page for images and captions.
    Merges nearby images (sub-plots) into single figures.
    Associates "Fig." text blocks with the nearest image group.
    """
    
    # 1. Get all image bounding boxes (rects)
    image_rects = []
    for img in page.get_images(full=True):
        try:
            rect = page.get_image_bbox(img)
            # Filter tiny images (icons, lines)
            if rect.width < 50 or rect.height < 50: 
                continue
            image_rects.append(rect)
        except Exception:
            continue

    if not image_rects:
        return []

    # 2. Merge overlapping or close rectangles (clustering subplots)
    changed = True
    while changed:
        changed = False
        new_rects = []
        while image_rects:
            r1 = image_rects.pop(0)
            merged = False
            for i, r2 in enumerate(new_rects):
                # *** CHANGE: Increased margin from 20 to 40 for adjacent subplots ***
                expanded_r2 = r2 + (-40, -40, 40, 40)
                
                if expanded_r2.intersects(r1):
                    new_rects[i] = r2 | r1 # Union
                    merged = True
                    changed = True
                    break
            if not merged:
                new_rects.append(r1)
        image_rects = new_rects

    # 3. Find Caption Text Blocks
    text_blocks = page.get_text("blocks")
    captions = []
    
    # Enhanced Regex (as agreed): More inclusive for common scientific labels
    fig_pattern = re.compile(r"^\s*(?:Fig\.?|Figure|Scheme|Chart|Panel|Box|A\.|B\.|C\.|D\.)\s*\d*", re.IGNORECASE)

    # First pass: find all text blocks that start a caption
    initial_caption_blocks = []
    for block in text_blocks:
        b_text = block[4]
        if fig_pattern.match(b_text):
            initial_caption_blocks.append(block)

    # Second pass: merge subsequent text blocks into the initial caption block
# We use a set of block numbers to avoid using the same text block in multiple captions
    used_block_numbers = set()
    
    for i, start_block in enumerate(initial_caption_blocks):
        start_block_number = start_block[5]
        # Skip if this block was already used as a continuation of a previous caption
        if start_block_number in used_block_numbers:
            continue
            
        full_text = start_block[4].strip()
        full_rect = pymupdf.Rect(start_block[:4])
        
        # Add the starting block number to the used set
        used_block_numbers.add(start_block_number)

        # Iterate through subsequent blocks to find continuations
        # The logic is: look for blocks that are vertically close AND horizontally aligned
        for j in range(start_block_number + 1, len(text_blocks)):
            next_block = text_blocks[j]
            next_rect = pymupdf.Rect(next_block[:4])
            next_text = next_block[4].strip()
            next_block_number = next_block[5]

            # 1. Check Proximity: The next block must be immediately below (Y-proximity)
            # A common line spacing is around 12-15 points. We use 30 as a generous vertical gap for line continuation.
            y_proximity = next_rect.y0 < full_rect.y1 + 30 
            
            # 2. Check Alignment: The next block must be horizontally aligned with the start block.
            # Captions are often centered or full-width, so we check if the x0 is close to the starting block's x0.
            x_alignment = abs(next_rect.x0 - full_rect.x0) < 20
            
            # 3. Stop Conditions: Break if the continuation criteria fail OR if we hit another caption/figure start.
            if not y_proximity or not x_alignment or fig_pattern.match(next_text):
                 break
            
            # 4. Check for New Paragraph (Gutter Check): 
            # If the vertical gap is too large (e.g., > 1.5 times the generous line spacing), it's likely a new paragraph/body text.
            # We use 20 points as a safe threshold for the gap between the merged block's bottom and the new block's top.
            if next_rect.y0 - full_rect.y1 > 20: 
                break # New paragraph/body text detected

            # If all checks pass, merge the text and union the rectangles
            full_text += " " + next_text.replace('\n', ' ')
            full_rect |= next_rect
            used_block_numbers.add(next_block_number)

        captions.append({
            "rect": full_rect,
            "text": full_text
        })
    
    # 4. Match Captions to Image Groups (Logic remains the same)
    figures = []
    
    for img_rect in image_rects:
        best_caption = None
        min_dist = float('inf')
        
        for i, cap in enumerate(captions):
            # Calculate distance
            dist = 0
            # Vertical
            if cap["rect"].y0 >= img_rect.y1: 
                dist = cap["rect"].y0 - img_rect.y1
            elif cap["rect"].y1 <= img_rect.y0:
                dist = img_rect.y0 - cap["rect"].y1
            else:
                dist = 0
            
            # Horizontal center alignment penalty
            center_x_img = (img_rect.x0 + img_rect.x1) / 2
            center_x_cap = (cap["rect"].x0 + cap["rect"].x1) / 2
            dist += abs(center_x_img - center_x_cap) * 0.5
            
            if dist < min_dist and dist < 200:
                min_dist = dist
                best_caption = cap

        final_rect = img_rect
        caption_text = ""
        
        if best_caption:
            final_rect = img_rect | best_caption["rect"]
            caption_text = best_caption["text"]
            # Add padding for the screenshot
            final_rect = final_rect + (-5, -5, 5, 5)

        final_rect = final_rect & page.rect

        figures.append({
            "rect": final_rect,
            "caption": caption_text
        })

    return figures




# === Chunk Generator with Metadata ===
# def extract_chunks_with_metadata(filepath: str) -> Tuple[List[Tuple[str, int]], Dict[str, str]]:
#     """
#     Extract chunks of text with page numbers and collect metadata.
#     Always run LLM-based metadata extraction, merged with PyMuPDF.
#     """    
#     chunks_with_page = []
#     first_pages_text = ""

#     with pymupdf.open(filepath) as doc:
#         metadata = doc.metadata or {}
#         for page_number, page in enumerate(doc, start=1):
#             text = page.get_text()
#             if page_number <= 10:
#                 first_pages_text += "\n" + text                         
#             if not text.strip():
#                 continue
#             page_chunks = get_text_chunks_recursive(text)
#             for chunk in page_chunks:
#                 chunks_with_page.append((chunk, page_number))

#         # Extract year from creationDate (i.e. from PDF built-in metadata)
#         creation_date = metadata.get("creationDate")
#         year = None
#         if creation_date:
#             try:
#                 clean_date = creation_date.lstrip("D:")
#                 dt = datetime.strptime(clean_date[:14], "%Y%m%d%H%M%S")
#                 year = str(dt.year)
#             except Exception:
#                 pass

#         # Extract metadata from PDF built-in metadata
#         pdf_title = metadata.get("title")
#         pdf_authors = metadata.get("author")
#         pdf_keywords = metadata.get("keywords")

#         # Convert to lists if single string
#         pdf_authors = to_list(metadata.get("author"))
#         pdf_keywords = to_list(metadata.get("keywords"))        

#         # # Convert to lists if single string
#         # pdf_authors = [pdf_authors] if isinstance(pdf_authors, str) else (pdf_authors or [])
#         # pdf_keywords = [pdf_keywords] if isinstance(pdf_keywords, str) else (pdf_keywords or [])

#         # Always run LLM for metadata
#         llm_meta = extract_metadata_with_llm(first_pages_text)

#         # Merge results (LLM takes priority if non-empty)
#         title = llm_meta.title or pdf_title
#         authors = list({*pdf_authors, *llm_meta.authors})
#         keywords = list({*pdf_keywords, *llm_meta.keywords})
#         publication_year = llm_meta.publication_year or year or ""
#         summary = llm_meta.summary or ""

#     return chunks_with_page, {
#         "file_title": title,
#         "authors": authors,
#         "keywords": keywords,
#         "creation_date": creation_date,
#         "publication_year": publication_year,
#         "summary": summary
#     }
# def extract_content_with_metadata(filepath: str, file_hash: str) -> Tuple[List, List, Dict]:
#     """
#     Extracts Text Chunks AND Image Figures.
#     Returns:
#         text_chunks: List[(text, page_num)]
#         image_chunks: List[{'description': str, 'page': int, 'path': str}]
#         doc_metadata: Dict
#     """
#     chunks_with_page = []
#     extracted_images = []
#     first_pages_text = ""
    
#     # Open PDF
#     doc = pymupdf.open(filepath)
#     metadata = doc.metadata or {}
    
#     # 1. Iterate Pages for Text and Images
#     for page_number, page in enumerate(doc, start=1):
        
#         # --- A. Text Extraction ---
#         text = page.get_text()
#         if page_number <= 10:
#             first_pages_text += "\n" + text
        
#         if text.strip():
#             page_chunks = get_text_chunks_recursive(text)
#             for chunk in page_chunks:
#                 chunks_with_page.append((chunk, page_number))

#         # --- B. Image Extraction ---
#         image_list = page.get_images(full=True)
        
#         for img_index, img in enumerate(image_list):
#             xref = img[0]
#             base_image = doc.extract_image(xref)
#             image_bytes = base_image["image"]
#             ext = base_image["ext"]
            
#             # Filter small images (logos, icons, layout lines)
#             try:
#                 pil_img = Image.open(io.BytesIO(image_bytes))
#                 width, height = pil_img.size
#                 # Skip if image is too small (e.g., less than 200x200 pixels)
#                 if width < 200 or height < 200:
#                     continue
#             except Exception:
#                 continue

#             # Save Image locally
#             image_filename = f"{file_hash}_p{page_number}_{img_index}.{ext}"
#             image_path = os.path.join(IMAGES_FOLDER, image_filename)
            
#             with open(image_path, "wb") as img_file:
#                 img_file.write(image_bytes)
            
#             # Encode for GPT-4o
#             base64_img = base64.b64encode(image_bytes).decode('utf-8')
            
#             # Generate Description
#             print(f"   > Analyzing figure on page {page_number}...")
#             try:
#                 description = describe_image_with_gpt4o(base64_img)
#                 extracted_images.append({
#                     "description": description,
#                     "page_number": page_number,
#                     "image_path": image_filename # Store relative filename or full path
#                 })
#             except Exception as e:
#                 print(f"   ! Failed to describe image: {e}")

#     # 2. Metadata Extraction (Logic unchanged)
#     creation_date = metadata.get("creationDate")
#     year = None
#     if creation_date:
#         try:
#             clean_date = creation_date.lstrip("D:")
#             dt = datetime.strptime(clean_date[:14], "%Y%m%d%H%M%S")
#             year = str(dt.year)
#         except Exception:
#             pass

#     pdf_authors = to_list(metadata.get("author"))
#     pdf_keywords = to_list(metadata.get("keywords"))       
    
#     llm_meta = extract_metadata_with_llm(first_pages_text)

#     title = llm_meta.title or metadata.get("title")
#     authors = list({*pdf_authors, *llm_meta.authors})
#     keywords = list({*pdf_keywords, *llm_meta.keywords})
#     publication_year = llm_meta.publication_year or year or ""
#     summary = llm_meta.summary or ""

#     return chunks_with_page, extracted_images, {
#         "file_title": title,
#         "authors": authors,
#         "keywords": keywords,
#         "creation_date": creation_date,
#         "publication_year": publication_year,
#         "summary": summary
#     }
def extract_content_with_metadata(filepath: str, file_hash: str) -> Tuple[List, List, Dict]:
    chunks_with_page = []
    extracted_images = []
    first_pages_text = ""
    
    doc = pymupdf.open(filepath)
    metadata = doc.metadata or {}
    
    for page_number, page in enumerate(doc, start=1):
        
        # --- A. Text Extraction ---
        text = page.get_text()
        if page_number <= 10:
            first_pages_text += "\n" + text
        
        if text.strip():
            page_chunks = get_text_chunks_recursive(text)
            for chunk in page_chunks:
                chunks_with_page.append((chunk, page_number))

        # --- B. Smart Figure Extraction ---
        # Instead of raw extraction, we use the visual identification logic
        figures = identify_figures_on_page(page)
        
        # Check that the IMAGES_FOLDER exists and is accessible
        if not os.path.isdir(IMAGES_FOLDER):
            print(f"   ! ERROR: IMAGES_FOLDER path does not exist or is not a directory: {IMAGES_FOLDER}")
            # Ensure folder is created/re-checked, though it should be at the start
            os.makedirs(IMAGES_FOLDER, exist_ok=True)

        for fig_idx, fig in enumerate(figures):
            
            # 1. Render the specific area of the page (Image + Caption)
            try:
                # Use a high DPI for better quality vision model input
                pix = page.get_pixmap(clip=fig["rect"], dpi=200) 
            except Exception as e:
                print(f"   ! Failed to create pixmap for figure on page {page_number}: {e}")
                continue
            
            # Skip if result is empty or tiny
            if pix.width < 100 or pix.height < 100:
                continue

            image_filename = f"{file_hash}_p{page_number}_fig{fig_idx}.png"
            image_path = os.path.join(IMAGES_FOLDER, image_filename)
            
            # 2. Save the Pixmap (rendered image) to disk
            saved_successfully = False
            try:
                # Use .save() on the pymupdf pixmap object
                pix.save(image_path)
                saved_successfully = True
                # CRITICAL DEBUG: Check if the file actually exists after saving
                if os.path.exists(image_path):
                    print(f"   > Image SAVED successfully to: {image_path}")
                else:
                    # This happens if pix.save() returns without error but the file is not written (e.g., permission issue)
                    print(f"   ! Image SAVE failed (File not found after pix.save()): {image_path}")
                    saved_successfully = False
                    
            except Exception as e:
                print(f"   ! Error saving image file {image_path}. Check permissions or file path: {e}")
                
            if not saved_successfully:
                continue # Skip this figure if we can't save it
            
            # 3. Convert the saved file to base64 for the API call
            base64_img = ""
            try:
                with open(image_path, "rb") as img_f:
                    base64_img = base64.b64encode(img_f.read()).decode('utf-8')
            except Exception as e:
                print(f"   ! Error reading saved image file {image_path} for encoding: {e}")
                continue # Skip if we can't read the file back
            
            # 4. Analyze the image with GPT-4o
            print(f"   > Analyzing Figure {fig_idx+1} on page {page_number} (Caption found: {bool(fig['caption'])})...")
            
            try:
                # Pass both the image and the extracted caption to the LLM
                description = describe_image_with_gpt4o(base64_img, caption=fig["caption"])
                
                extracted_images.append({
                    "description": description,
                    "caption": fig["caption"], # Store caption in metadata too
                    "page_number": page_number,
                    "image_path": image_filename
                })
            except Exception as e:
                print(f"   ! Failed to describe image: {e}")

    # Metadata extraction logic (unchanged)
    creation_date = metadata.get("creationDate")
    year = None
    if creation_date:
        try:
            clean_date = creation_date.lstrip("D:")
            dt = datetime.strptime(clean_date[:14], "%Y%m%d%H%M%S")
            year = str(dt.year)
        except Exception:
            pass

    pdf_authors = to_list(metadata.get("author"))
    pdf_keywords = to_list(metadata.get("keywords"))        
    
    llm_meta = extract_metadata_with_llm(first_pages_text)

    title = llm_meta.title or metadata.get("title")
    authors = list({*pdf_authors, *llm_meta.authors})
    keywords = list({*pdf_keywords, *llm_meta.keywords})
    publication_year = llm_meta.publication_year or year or ""
    summary = llm_meta.summary or ""

    return chunks_with_page, extracted_images, {
        "file_title": title,
        "authors": authors,
        "keywords": keywords,
        "creation_date": creation_date,
        "publication_year": publication_year,
        "summary": summary
    }


# def ingest_documents(file_path: str, qdrant_url: str, qdrant_api_key: str, collection_name: str, verbose: bool = False):
#     # This function will contain the core logic of your existing script.
    
#     # Initialize embedding model and Qdrant client
#     embedding_model = OpenAIEmbeddings()
#     qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

#     # Make sure your collection and indexes exist
#     if not qdrant_client.collection_exists(collection_name=collection_name):
#         qdrant_client.create_collection(
#             collection_name=collection_name,
#             vectors_config=VectorParams(size=embedding_model.dimensions, distance=Distance.COSINE)
#         )

#     # Create metadata indexes
#     # Note: Added "image_path" to index if you want to filter by presence of images later
#     for field in ["file_hash", "file_name", "file_title", "authors", "keywords", "creation_date", "page_number", "type", "image_path"]:
#         qdrant_client.create_payload_index(
#             collection_name=collection_name, 
#             field_name=field, 
#             field_schema=PayloadSchemaType.KEYWORD
#         )

#     # Create the text index                          
#     qdrant_client.create_payload_index(
#         collection_name=collection_name, 
#         field_name="text", 
#         field_schema=PayloadSchemaType.TEXT
#     )

#     # Ingestion logic for a single file
#     filename = os.path.basename(file_path)
#     file_hash = get_file_hash(file_path)

#     # Check for existing file by hash to avoid re-ingestion
#     existing = qdrant_client.scroll(
#         collection_name=collection_name,
#         scroll_filter={"must": [{"key": "file_hash", "match": {"value": file_hash}}]},
#         limit=1
#     )
#     if existing[0]:
#         print(f"✔ Skipping (already indexed): {filename}")
#         return # Exit the function for this file

#     print(f"→ Processing: {filename}")
#     # try:
#     #     chunks_with_meta, doc_metadata = extract_chunks_with_metadata(file_path)
#     #     texts = [chunk for chunk, _ in chunks_with_meta]
#     #     page_numbers = [page for _, page in chunks_with_meta]


#     #     # --- Build the Metadata Header for Chunks ---
#     #     title = doc_metadata.get("file_title") or "[Unknown Title]"
#     #     # Join authors into a single string
#     #     authors = ", ".join(doc_metadata.get("authors", [])) or "[Unknown Author(s)]"
#     #     year = doc_metadata.get("publication_year") or "[Unknown Year]"
#     #     summary_text = doc_metadata.get("summary") or "[No Summary Available]"
        
#     #     # 1. REGULAR CHUNK DEFINITION
#     #     # Create the standard header string exactly as requested
#     #     header = (
#     #         f"Document Title: {title}\n"
#     #         f"Author(s): {authors}\n"
#     #         f"Year of publication: {year}\n"
#     #         f"\n"
#     #         f"Chunk text: \n"          
#     #     )        

#     #     # --- Prepend Header and Prepare for Embedding ---
#     #     # The new list of texts to embed, including the header
#     #     texts_to_embed = [header + chunk for chunk in texts]

#     #     # Embed the new texts
#     #     vectors = embedding_model.embed_documents(texts_to_embed)

#     #     if verbose:
#     #         chunk_lengths = [len(c) for c in texts_to_embed] # Calculate lengths of the *new* texts
#     #         print(f"    - {len(texts)} chunks extracted")
#     #         print(f"→ Min: {min(chunk_lengths)}, Max: {max(chunk_lengths)}, Median: {int(statistics.median(chunk_lengths))}")

#     #     points = []
#     #     # Iterate over the texts_to_embed, which includes the header
#     #     for chunk_with_header, original_chunk, vec, page_num in zip(
#     #         texts_to_embed, texts, vectors, page_numbers
#     #     ):
            
#     #         chunk_summary = summarize_text(
#     #             chunk_with_header,
#     #             provider='groq',
#     #             model=config.SUMMARIZATION_MODEL,
#     #             temperature=config.SUMMARIZATION_MODEL_TEMPERATURE,
#     #             max_tokens=config.SUMMARIZATION_MODEL_MAX_TOKENS,
#     #             template_name="document_chunk_summarization")
#     #         chunk_summary = chunk_summary.summary.strip() # CHECK THIS

#     #         points.append(PointStruct(
#     #             id=str(uuid.uuid4()),
#     #             vector=vec,
#     #             payload={
#     #                 "file_name": filename,
#     #                 "file_hash": file_hash,
#     #                 "file_title": doc_metadata.get("file_title"),
#     #                 "authors": doc_metadata.get("authors"), # Keep the list version for metadata filtering
#     #                 "keywords": doc_metadata.get("keywords"),
#     #                 "creation_date": doc_metadata.get("creation_date"),
#     #                 "year": doc_metadata.get("publication_year"),
#     #                 "page_number": str(page_num),
#     #                 # Store the header + text for better RAG context
#     #                 "text": chunk_with_header, 
#     #                 "type": "chunk", # for regular chunks
#     #                 # Use the original chunk for summarization to avoid LLM repeating the header
#     #                 # "summary": summarize_chunk(original_chunk) 
#     #                 "summary": chunk_summary
#     #             }
#     #         ))

#     #     # 2. DOCUMENT SUMMARY DEFINITION

#     #     # Embed the document summary as a separate point
#     #     # Create the standard header string exactly as requested
#     #     header = (
#     #         f"Document Title: {title}\n"
#     #         f"Author(s): {authors}\n"
#     #         f"Year of publication: {year}\n"
#     #         f"\n"
#     #         f"Summary text: \n"          
#     #     )        

#     #     # --- Prepend Header and Prepare for Embedding ---
#     #     # including the header
#     #     summary_with_header = [header + summary_text]        
#     #     vector_summary = embedding_model.embed_documents(summary_with_header)[0] # here I need to unlist

#     #     points.append(PointStruct(
#     #         id=str(uuid.uuid4()),
#     #         vector=vector_summary,
#     #         payload={
#     #             "file_name": filename,
#     #             "file_hash": file_hash,
#     #             "file_title": doc_metadata.get("file_title"),
#     #             "authors": doc_metadata.get("authors"), # Keep the list version for metadata filtering
#     #             "keywords": doc_metadata.get("keywords"),
#     #             "creation_date": doc_metadata.get("creation_date"),
#     #             "year": doc_metadata.get("publication_year"),
#     #             "page_number": "0",  # No specific page number for the summary
#     #             # Store the header + text for better RAG context
#     #             "text": summary_with_header[0], # here I need to unlist
#     #             "type": "summary", # for full document summary
#     #             # Use the original chunk for summarization to avoid LLM repeating the header
#     #             "summary": "FULL_DOCUMENT_SUMMARY"
#     #         }
#     #     ))

#     #     # 3. Upsert points to Qdrant
#     #     qdrant_client.upsert(collection_name=collection_name, points=points)
#     #     print(f"✅ Indexed: {filename}")
#     try:
#         # Calls the new extraction function
#         text_chunks, image_chunks, doc_metadata = extract_content_with_metadata(file_path, file_hash)
        
#         points = []

#         # --- Metadata Header Prep ---
#         title = doc_metadata.get("file_title") or "[Unknown Title]"
#         authors = ", ".join(doc_metadata.get("authors", [])) or "[Unknown Author(s)]"
#         year = doc_metadata.get("publication_year") or "[Unknown Year]"
#         doc_summary_text = doc_metadata.get("summary") or "[No Summary]"

#         base_header = (
#             f"Document Title: {title}\n"
#             f"Author(s): {authors}\n"
#             f"Year of publication: {year}\n\n"
#         )

#         # ==========================================
#         # 1. PROCESS TEXT CHUNKS
#         # ==========================================
#         if text_chunks:
#             texts = [chunk for chunk, _ in text_chunks]
#             page_numbers = [page for _, page in text_chunks]
            
#             # Prepend Header
#             texts_to_embed = [f"{base_header}Chunk text:\n{chunk}" for chunk in texts]
            
#             # Embed
#             vectors = embedding_model.embed_documents(texts_to_embed)

#             for chunk_with_header, vec, page_num in zip(texts_to_embed, vectors, page_numbers):
                
#                 # Create short summary for payload
#                 chunk_summary_obj = summarize_text(
#                     chunk_with_header, provider='groq', model=config.SUMMARIZATION_MODEL,
#                     temperature=config.SUMMARIZATION_MODEL_TEMPERATURE, max_tokens=config.SUMMARIZATION_MODEL_MAX_TOKENS,
#                     template_name="document_chunk_summarization"
#                 )

#                 points.append(PointStruct(
#                     id=str(uuid.uuid4()),
#                     vector=vec,
#                     payload={
#                         "file_name": filename,
#                         "file_hash": file_hash,
#                         "file_title": title,
#                         "authors": doc_metadata.get("authors"),
#                         "keywords": doc_metadata.get("keywords"),
#                         "year": year,
#                         "page_number": str(page_num),
#                         "text": chunk_with_header,
#                         "type": "chunk", # Regular text
#                         "summary": chunk_summary_obj.summary.strip(),
#                         "image_path": None # Explicitly null for text
#                     }
#                 ))

#         # ==========================================
#         # 2. PROCESS IMAGE CHUNKS
#         # ==========================================
#         if image_chunks:
#             print(f"→ Processing {len(image_chunks)} figures...")
            
#             # Prepare image description texts (Header + Description)
#             img_texts_to_embed = [
#                 f"{base_header}Figure Description:\n{img['description']}" 
#                 for img in image_chunks
#             ]
            
#             # Embed image descriptions
#             img_vectors = embedding_model.embed_documents(img_texts_to_embed)
            
#             for img_data, text_content, vec in zip(image_chunks, img_texts_to_embed, img_vectors):
#                 points.append(PointStruct(
#                     id=str(uuid.uuid4()),
#                     vector=vec,
#                     payload={
#                         "file_name": filename,
#                         "file_hash": file_hash,
#                         "file_title": title,
#                         "authors": doc_metadata.get("authors"),
#                         "keywords": doc_metadata.get("keywords"),
#                         "year": year,
#                         "page_number": str(img_data['page_number']),
#                         "text": text_content, # The vector searches against this description
#                         "type": "figure", # <--- NEW KEYWORD
#                         "summary": "FIGURE_DESCRIPTION",
#                         "image_path": img_data['image_path'] # <--- Store local path
#                     }
#                 ))

#         # ==========================================
#         # 3. PROCESS DOC SUMMARY
#         # ==========================================
#         summary_text_final = f"{base_header}Summary text:\n{doc_summary_text}"
#         vector_summary = embedding_model.embed_documents([summary_text_final])[0]
        
#         points.append(PointStruct(
#             id=str(uuid.uuid4()),
#             vector=vector_summary,
#             payload={
#                 "file_name": filename,
#                 "file_hash": file_hash,
#                 "file_title": title,
#                 "authors": doc_metadata.get("authors"),
#                 "keywords": doc_metadata.get("keywords"),
#                 "year": year,
#                 "page_number": "0",
#                 "text": summary_text_final,
#                 "type": "summary",
#                 "summary": "FULL_DOCUMENT_SUMMARY",
#                 "image_path": None
#             }
#         ))
def ingest_documents(file_path: str, qdrant_url: str, qdrant_api_key: str, collection_name: str, verbose: bool = False):
    
    embedding_model = OpenAIEmbeddings()
    qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    if not qdrant_client.collection_exists(collection_name=collection_name):
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=embedding_model.dimensions, distance=Distance.COSINE)
        )

    for field in ["file_hash", "file_name", "file_title", "authors", "keywords", "creation_date", "page_number", "type", "image_path"]:
        qdrant_client.create_payload_index(
            collection_name=collection_name, 
            field_name=field, 
            field_schema=PayloadSchemaType.KEYWORD
        )

    qdrant_client.create_payload_index(
        collection_name=collection_name, 
        field_name="text", 
        field_schema=PayloadSchemaType.TEXT
    )

    filename = os.path.basename(file_path)
    file_hash = get_file_hash(file_path)

    existing = qdrant_client.scroll(
        collection_name=collection_name,
        scroll_filter={"must": [{"key": "file_hash", "match": {"value": file_hash}}]},
        limit=1
    )
    if existing[0]:
        print(f"✔ Skipping (already indexed): {filename}")
        return

    print(f"→ Processing: {filename}")

    try:
        text_chunks, image_chunks, doc_metadata = extract_content_with_metadata(file_path, file_hash)
        
        points = []
        title = doc_metadata.get("file_title") or "[Unknown Title]"
        authors = ", ".join(doc_metadata.get("authors", [])) or "[Unknown Author(s)]"
        year = doc_metadata.get("publication_year") or "[Unknown Year]"
        doc_summary_text = doc_metadata.get("summary") or "[No Summary]"

        base_header = (
            f"Document Title: {title}\n"
            f"Author(s): {authors}\n"
            f"Year of publication: {year}\n\n"
        )

        # 1. TEXT CHUNKS
        if text_chunks:
            texts = [chunk for chunk, _ in text_chunks]
            page_numbers = [page for _, page in text_chunks]
            texts_to_embed = [f"{base_header}Chunk text:\n{chunk}" for chunk in texts]
            vectors = embedding_model.embed_documents(texts_to_embed)

            for chunk_with_header, vec, page_num in zip(texts_to_embed, vectors, page_numbers):
                chunk_summary_obj = summarize_text(
                    chunk_with_header, provider='groq', model=config.SUMMARIZATION_MODEL,
                    temperature=config.SUMMARIZATION_MODEL_TEMPERATURE, max_tokens=config.SUMMARIZATION_MODEL_MAX_TOKENS,
                    template_name="document_chunk_summarization"
                )
                points.append(PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vec,
                    payload={
                        "file_name": filename,
                        "file_hash": file_hash,
                        "file_title": title,
                        "authors": doc_metadata.get("authors"),
                        "keywords": doc_metadata.get("keywords"),
                        "year": year,
                        "page_number": str(page_num),
                        "text": chunk_with_header,
                        "type": "chunk",
                        "summary": chunk_summary_obj.summary.strip(),
                        "image_path": None
                    }
                ))

        # 2. FIGURE CHUNKS
        if image_chunks:
            print(f"→ Processing {len(image_chunks)} figures...")
            
            # Embed Metadata + Caption + Generated Description
            img_texts_to_embed = [
                f"{base_header}Figure Caption: {img['caption']}\nDescription:\n{img['description']}" 
                for img in image_chunks
            ]
            
            img_vectors = embedding_model.embed_documents(img_texts_to_embed)
            
            for img_data, text_content, vec in zip(image_chunks, img_texts_to_embed, img_vectors):
                points.append(PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vec,
                    payload={
                        "file_name": filename,
                        "file_hash": file_hash,
                        "file_title": title,
                        "authors": doc_metadata.get("authors"),
                        "keywords": doc_metadata.get("keywords"),
                        "year": year,
                        "page_number": str(img_data['page_number']),
                        "text": text_content,
                        "type": "figure",
                        "summary": "FIGURE_DESCRIPTION",
                        "image_path": img_data['image_path']
                    }
                ))

        # 3. DOC SUMMARY
        summary_text_final = f"{base_header}Summary text:\n{doc_summary_text}"
        vector_summary = embedding_model.embed_documents([summary_text_final])[0]
        
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=vector_summary,
            payload={
                "file_name": filename,
                "file_hash": file_hash,
                "file_title": title,
                "authors": doc_metadata.get("authors"),
                "keywords": doc_metadata.get("keywords"),
                "year": year,
                "page_number": "0",
                "text": summary_text_final,
                "type": "summary",
                "summary": "FULL_DOCUMENT_SUMMARY",
                "image_path": None
            }
        ))

        # Upsert
        qdrant_client.upsert(collection_name=collection_name, points=points)
        print(f"✅ Indexed: {filename} ({len(points)} points)")

        if verbose:   
            # Optional: show sample payloads
            sample, _ = qdrant_client.scroll(collection_name=collection_name, limit=2)
            for pt in sample:
                print(f"Sample payload:\n{pt.payload}")                 

    except Exception as e:
        # Custom exception for better error handling in the API endpoint
        raise IngestionError(f"Error processing {filename}: {e}")

# Create a simple custom exception for clarity
class IngestionError(Exception):
    pass