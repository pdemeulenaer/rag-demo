import os
import httpx
import hashlib
import uuid
import pymupdf
# from mineru.parsers import PDFParser
from unstructured.partition.pdf import partition_pdf
from langchain.text_splitter import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance, PayloadSchemaType
from typing import List, Generator, Tuple, Dict
import statistics
# from huggingface_hub import InferenceClient
# from langchain.embeddings.base import Embeddings
from dotenv import load_dotenv

from .utils import (
    load_config,
    RemoteEmbeddingsAPI,
)

load_dotenv()
config = load_config()

# === Config ===
QDRANT_URL = os.getenv("QDRANT_URL") 
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
# HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
# COLLECTION_NAME = config["collection"] # "test_collection2"
PDF_FOLDER = os.path.join(os.path.dirname(__file__), "folder")
EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL")




# class HFCLIPTextEmbedding(Embeddings):
#     def __init__(self, model_name: str, api_token: str):
#         self.model_name = model_name  # Store model_name as instance variable
#         self.client = InferenceClient(provider="hf-inference", api_key=api_token)
    
#     def embed_query(self, text: str) -> List[float]:  # Remove model_name parameter
#         return self.client.feature_extraction(text, model=self.model_name)  # text as first positional argument
    
#     def embed_documents(self, texts: List[str]) -> List[List[float]]:
#         return [self.embed_query(t) for t in texts]  # No need to pass model_name here


# === File Hashing ===
def get_file_hash(filepath) -> str:
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# === Chunking ===
def get_text_chunks_recursive(text, config) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config["chunking"]["chunk_size"],
        chunk_overlap=config["chunking"]["chunk_overlap"],
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    return splitter.split_text(text)


# # === Chunk Generator with Metadata ===
# def extract_chunks_with_metadata(filepath: str, config) -> Tuple[List[Tuple[str, int]], Dict[str, str]]:
#     chunks_with_page = []
#     with pymupdf.open(filepath) as doc:
#         metadata = doc.metadata or {}
#         for page_number, page in enumerate(doc, start=1):
#             text = page.get_text()
#             if not text.strip():
#                 continue
#             page_chunks = get_text_chunks_recursive(text, config)
#             for chunk in page_chunks:
#                 chunks_with_page.append((chunk, page_number))
#     return chunks_with_page, {
#         "file_title": metadata.get("title"),
#         "authors": metadata.get("author"),
#         "keywords": metadata.get("keywords"),
#         "creation_date": metadata.get("creationDate")
#     }


def extract_chunks_with_metadata(filepath: str, config) -> Tuple[List[Tuple[str, str]], Dict[str, str]]:
    """
    Extract semantically structured chunks from a PDF using unstructured.
    Each chunk is associated with a section heading.
    """
    # Extract elements with unstructured
    elements = partition_pdf(
        filename=filepath,
        strategy="hi_res",  # High-resolution strategy for better accuracy
        include_page_breaks=True,  # Preserve page boundaries if needed
    )

    chunks_with_section = []
    current_heading = "Unknown"
    current_content = []

    # Group elements into sections based on headings
    for element in elements:
        element_type = element.category  # e.g., "Title", "NarrativeText"
        text = element.text.strip()

        if not text:
            continue

        if element_type == "Title":
            # Save previous section (if any)
            if current_content:
                full_markdown = f"{current_heading}\n\n{''.join(current_content).strip()}"
                chunks_with_section.append((full_markdown, current_heading))
                current_content = []
            current_heading = text
        else:
            # Append text to current section (e.g., NarrativeText, ListItem)
            current_content.append(text + "\n")

    # Save the last section
    if current_content:
        full_markdown = f"{current_heading}\n\n{''.join(current_content).strip()}"
        chunks_with_section.append((full_markdown, current_heading))

    # Split large sections into smaller chunks using RecursiveCharacterTextSplitter
    final_chunks = []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config["chunking"]["chunk_size"],
        chunk_overlap=config["chunking"]["chunk_overlap"],
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    for chunk, heading in chunks_with_section:
        sub_chunks = splitter.split_text(chunk)
        for sub_chunk in sub_chunks:
            final_chunks.append((sub_chunk, heading))

    # Extract metadata using pymupdf (unchanged)
    with pymupdf.open(filepath) as doc:
        metadata = doc.metadata or {}

    return final_chunks, {
        "file_title": metadata.get("title", ""),
        "authors": metadata.get("author", ""),
        "keywords": metadata.get("keywords", ""),
        "creation_date": metadata.get("creationDate", "")
    }


# # === Optional: Summarization Stub ===
# def summarize_chunk(text: str) -> str:
#     # TODO: Replace with LLM summarization if needed
#     return text[:200] + "..." if len(text) > 200 else text  # Simple fallback summary


# === Summarization with Groq ===
def summarize_chunk(text: str, config) -> str:
    """
    Use Groq's Mixtral model to summarize a long chunk of text.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set in environment variables.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": config["summarization"]["model"],  # Handles up to 128k tokens
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that summarizes academic documents."},
            {"role": "user", "content": f"Summarize the following chunk:\n\n{text}"}
        ],
        "temperature": config["summarization"]["temperature"],
        "max_tokens": config["summarization"]["max_tokens"]  # output summary size: 256=2-3 sentences, 512~1 paragraph
    }

    try:
        response = httpx.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"⚠️ Groq summarization failed: {e}")
        return text[:200] + "..."  # Fallback



# === Ingestion Function ===
def ingest_folder_to_qdrant(folder_path: str, qdrant_url: str, qdrant_api_key: str, config):
    # if not HUGGINGFACE_API_TOKEN:
    #     raise ValueError("Missing HUGGINGFACE_API_TOKEN in .env")

    # Use HuggingFaceHub directly
    # embedding_model = HFCLIPTextEmbedding(
    #     model_name="sentence-transformers/all-MiniLM-L6-v2",
    #     api_token=HUGGINGFACE_API_TOKEN
    # )

    collection_name = config["collection"]  # Use config for collection name
    
    # Initialize embedding model using remote API
    embedding_model = RemoteEmbeddingsAPI(endpoint_url=EMBEDDING_API_URL)  

    qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    if not qdrant_client.collection_exists(collection_name=collection_name):
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )

    metadata_fields = [
        "file_hash",
        "file_name",
        "file_title",
        "authors",
        "keywords",
        "creation_date",
        "section",  # replacing "page_number" when using MinerU
    ]

    # Create metadata indexes
    for field in metadata_fields: 
        qdrant_client.create_payload_index(
            collection_name=collection_name,
            field_name=field,
            field_schema=PayloadSchemaType.KEYWORD
        )

    for filename in os.listdir(folder_path):
        if not filename.lower().endswith(".pdf"):
            continue

        filepath = os.path.join(folder_path, filename)
        file_hash = get_file_hash(filepath)

        # Skip already ingested files
        existing = qdrant_client.scroll(
            collection_name=collection_name,
            scroll_filter={"must": [{"key": "file_hash", "match": {"value": file_hash}}]},
            limit=1
        )
        if existing[0]:
            print(f"✔ Skipping (already indexed): {filename}")
            continue

        print(f"→ Processing: {filename}")
        chunks_with_meta, doc_metadata = extract_chunks_with_metadata(filepath, config)

        # Extract text chunks and page numbers
        # texts = [chunk for chunk, _ in chunks_with_meta]
        # page_numbers = [page for _, page in chunks_with_meta]

        # Extract section names and section headings
        texts = [chunk for chunk, _ in chunks_with_meta]
        section_names = [section for _, section in chunks_with_meta]        

        vectors = embedding_model.embed_documents(texts)

        chunk_lengths = [len(c) for c in texts]
        print(f"   - {len(texts)} chunks extracted")
        print(f"→ Min: {min(chunk_lengths)}, Max: {max(chunk_lengths)}, Median: {int(statistics.median(chunk_lengths))}")

        points = []
        # for chunk, vec, page_num in zip(texts, vectors, page_numbers):
        for chunk, vec, section_name in zip(texts, vectors, section_names):
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "file_name": filename,
                    "file_hash": file_hash,
                    "file_title": doc_metadata.get("file_title"),
                    "authors": doc_metadata.get("authors"),
                    "keywords": doc_metadata.get("keywords"),
                    "creation_date": doc_metadata.get("creation_date"),
                    # "page_number": str(page_num),
                    "section": section_name,
                    "text": chunk,
                    "summary": summarize_chunk(chunk, config)
                }
            ))

        qdrant_client.upsert(collection_name=collection_name, points=points)
        print(f"✅ Indexed: {filename}")

        # Optional: show sample payloads
        sample, _ = qdrant_client.scroll(collection_name=collection_name, limit=2)
        for pt in sample:
            print(f"Sample payload:\n{pt.payload}")


# === Run ===
if __name__ == "__main__":
    ingest_folder_to_qdrant(
        folder_path=PDF_FOLDER,
        qdrant_url=QDRANT_URL,
        qdrant_api_key=QDRANT_API_KEY,
        config=config
    )
