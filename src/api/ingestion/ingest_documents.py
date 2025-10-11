# src/api/ingestion/ingest_documents.py

import os
import httpx
import hashlib
import uuid
import json
import pymupdf
import re
from datetime import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance, PayloadSchemaType
from typing import List, Tuple, Dict
import statistics
from langchain.embeddings.base import Embeddings
from openai import OpenAI
import instructor
from pydantic import BaseModel, Field

from src.api.core.config import config
from src.api.rag.utils.utils import prompt_template_config, prompt_template_registry


# === Config ===
PDF_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/folder"))



# === OpenAI Embedding Class ===
client = OpenAI(api_key=config.OPENAI_API_KEY)
openai_client = instructor.from_openai(client) 
# Wrap OpenAI client with Instructor
# client = instructor.from_openai(OpenAI(api_key=OPENAI_API_KEY))
groq_client = instructor.from_openai(
    OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=config.GROQ_API_KEY
    )
)

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "authors": {
            "type": "array",
            "items": {"type": "string"}
        },
        "keywords": {
            "type": "array",
            "items": {"type": "string"}
        },
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
    summary: str = Field(..., description="The abstract or high-level summary of the document, if present. If not present, generate a brief summary from the provided text.")



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


# === Chunk Generator with Metadata ===
def extract_chunks_with_metadata(filepath: str) -> Tuple[List[Tuple[str, int]], Dict[str, str]]:
    """
    Extract chunks of text with page numbers and collect metadata.
    Always run LLM-based metadata extraction, merged with PyMuPDF.
    """    
    chunks_with_page = []
    first_pages_text = ""

    with pymupdf.open(filepath) as doc:
        metadata = doc.metadata or {}
        for page_number, page in enumerate(doc, start=1):
            text = page.get_text()
            if page_number <= 10:
                first_pages_text += "\n" + text                         
            if not text.strip():
                continue
            page_chunks = get_text_chunks_recursive(text)
            for chunk in page_chunks:
                chunks_with_page.append((chunk, page_number))

        # Extract year from creationDate
        creation_date = metadata.get("creationDate")
        year = None
        if creation_date:
            try:
                clean_date = creation_date.lstrip("D:")
                dt = datetime.strptime(clean_date[:14], "%Y%m%d%H%M%S")
                year = str(dt.year)
            except Exception:
                pass

        # Extract metadata from PDF
        pdf_title = metadata.get("title")
        pdf_authors = metadata.get("author")
        pdf_keywords = metadata.get("keywords")

        # Convert to lists if single string
        pdf_authors = to_list(metadata.get("author"))
        pdf_keywords = to_list(metadata.get("keywords"))        

        # # Convert to lists if single string
        # pdf_authors = [pdf_authors] if isinstance(pdf_authors, str) else (pdf_authors or [])
        # pdf_keywords = [pdf_keywords] if isinstance(pdf_keywords, str) else (pdf_keywords or [])

        # Always run LLM for metadata
        llm_meta = extract_metadata_with_llm(first_pages_text)

        # Merge results (LLM takes priority if non-empty)
        title = llm_meta.title or pdf_title
        authors = list({*pdf_authors, *llm_meta.authors})
        keywords = list({*pdf_keywords, *llm_meta.keywords})
        summary = llm_meta.summary or ""

    return chunks_with_page, {
        "file_title": title,
        "authors": authors,
        "keywords": keywords,
        "creation_date": creation_date,
        "year": year,
        "summary": summary
    }


# === Summarization with Groq ===
def summarize_chunk(text: str) -> str:
    """
    Use Groq's Mixtral model to summarize a long chunk of text.
    """
    api_key = config.GROQ_API_KEY # os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set in environment variables.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": config.SUMMARIZATION_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that summarizes academic documents."},
            {"role": "user", "content": f"Summarize the following chunk:\n\n{text}"}
        ],
        "temperature": config.SUMMARIZATION_MODEL_TEMPERATURE, 
        "max_tokens": config.SUMMARIZATION_MODEL_MAX_TOKENS 
    }

    try:
        response = httpx.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"⚠️ Groq summarization failed: {e}")
        return text[:200] + "..."




def ingest_documents(file_path: str, qdrant_url: str, qdrant_api_key: str, collection_name: str, verbose: bool = False):
    # This function will contain the core logic of your existing script.
    
    # Initialize embedding model and Qdrant client
    embedding_model = OpenAIEmbeddings()
    qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    # Make sure your collection and indexes exist
    if not qdrant_client.collection_exists(collection_name=collection_name):
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=embedding_model.dimensions, distance=Distance.COSINE)
        )

    # Create metadata indexes
    for field in ["file_hash", "file_name", "file_title", "authors", "keywords", "creation_date", "page_number", "type"]:
        qdrant_client.create_payload_index(
            collection_name=collection_name, 
            field_name=field, 
            field_schema=PayloadSchemaType.KEYWORD
        )

    # Create the text index                          
    qdrant_client.create_payload_index(
        collection_name=collection_name, 
        field_name="text", 
        field_schema=PayloadSchemaType.TEXT
    )

    # Ingestion logic for a single file
    filename = os.path.basename(file_path)
    file_hash = get_file_hash(file_path)

    # Check for existing file by hash to avoid re-ingestion
    existing = qdrant_client.scroll(
        collection_name=collection_name,
        scroll_filter={"must": [{"key": "file_hash", "match": {"value": file_hash}}]},
        limit=1
    )
    if existing[0]:
        print(f"✔ Skipping (already indexed): {filename}")
        return # Exit the function for this file

    print(f"→ Processing: {filename}")
    try:
        chunks_with_meta, doc_metadata = extract_chunks_with_metadata(file_path)
        texts = [chunk for chunk, _ in chunks_with_meta]
        page_numbers = [page for _, page in chunks_with_meta]


        # --- Build the Metadata Header for Chunks ---
        title = doc_metadata.get("file_title") or "[Unknown Title]"
        # Join authors into a single string
        authors = ", ".join(doc_metadata.get("authors", [])) or "[Unknown Author(s)]"
        year = doc_metadata.get("year") or "[Unknown Year]"
        summary_text = doc_metadata.get("summary") or "[No Summary Available]"
        
        # 1. REGULAR CHUNK DEFINITION
        # Create the standard header string exactly as requested
        header = (
            f"Document Title: {title}\n"
            f"Author(s): {authors}\n"
            f"Year of publication: {year}\n"
            f"\n"
            f"Chunk text: \n"          
        )        

        # --- Prepend Header and Prepare for Embedding ---
        # The new list of texts to embed, including the header
        texts_to_embed = [header + chunk for chunk in texts]

        # Embed the new texts
        vectors = embedding_model.embed_documents(texts_to_embed)

        if verbose:
            chunk_lengths = [len(c) for c in texts_to_embed] # Calculate lengths of the *new* texts
            print(f"    - {len(texts)} chunks extracted")
            print(f"→ Min: {min(chunk_lengths)}, Max: {max(chunk_lengths)}, Median: {int(statistics.median(chunk_lengths))}")

        points = []
        # Iterate over the texts_to_embed, which includes the header
        for chunk_with_header, original_chunk, vec, page_num in zip(
            texts_to_embed, texts, vectors, page_numbers
        ):
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "file_name": filename,
                    "file_hash": file_hash,
                    "file_title": doc_metadata.get("file_title"),
                    "authors": doc_metadata.get("authors"), # Keep the list version for metadata filtering
                    "keywords": doc_metadata.get("keywords"),
                    "creation_date": doc_metadata.get("creation_date"),
                    "year": doc_metadata.get("year"),
                    "page_number": str(page_num),
                    # Store the header + text for better RAG context
                    "text": chunk_with_header, 
                    "type": "chunk", # for regular chunks
                    # Use the original chunk for summarization to avoid LLM repeating the header
                    "summary": summarize_chunk(original_chunk) 
                }
            ))

        # 2. DOCUMENT SUMMARY DEFINITION

        # Embed the document summary as a separate point
        # Create the standard header string exactly as requested
        header = (
            f"Document Title: {title}\n"
            f"Author(s): {authors}\n"
            f"Year of publication: {year}\n"
            f"\n"
            f"Summary text: \n"          
        )        

        # --- Prepend Header and Prepare for Embedding ---
        # including the header
        summary_with_header = [header + summary_text]        
        vector_summary = embedding_model.embed_documents(summary_with_header)[0] # here I need to unlist

        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=vector_summary,
            payload={
                "file_name": filename,
                "file_hash": file_hash,
                "file_title": doc_metadata.get("file_title"),
                "authors": doc_metadata.get("authors"), # Keep the list version for metadata filtering
                "keywords": doc_metadata.get("keywords"),
                "creation_date": doc_metadata.get("creation_date"),
                "year": doc_metadata.get("year"),
                "page_number": "0",  # No specific page number for the summary
                # Store the header + text for better RAG context
                "text": summary_with_header[0], # here I need to unlist
                "type": "summary", # for full document summary
                # Use the original chunk for summarization to avoid LLM repeating the header
                "summary": "FULL_DOCUMENT_SUMMARY"
            }
        ))

        # 3. Upsert points to Qdrant
        qdrant_client.upsert(collection_name=collection_name, points=points)
        print(f"✅ Indexed: {filename}")

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