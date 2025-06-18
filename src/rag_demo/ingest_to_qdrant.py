import os
import httpx
import hashlib
import uuid
import pymupdf
from langchain.text_splitter import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance, PayloadSchemaType
from typing import List, Generator, Tuple, Dict
import statistics
from huggingface_hub import InferenceClient
from langchain.embeddings.base import Embeddings
from dotenv import load_dotenv

from .utils import (
    load_config,
    RemoteEmbeddingsAPI,
)

load_dotenv()

# === Config ===
QDRANT_URL = os.getenv("QDRANT_URL") 
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
# HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
COLLECTION_NAME = "test_collection2"
PDF_FOLDER = os.path.join(os.path.dirname(__file__), "folder")
EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL")

config = load_config()


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


# === Chunk Generator with Metadata ===
def extract_chunks_with_metadata(filepath: str, config) -> Tuple[List[Tuple[str, int]], Dict[str, str]]:
    chunks_with_page = []
    with pymupdf.open(filepath) as doc:
        metadata = doc.metadata or {}
        for page_number, page in enumerate(doc, start=1):
            text = page.get_text()
            if not text.strip():
                continue
            page_chunks = get_text_chunks_recursive(text, config)
            for chunk in page_chunks:
                chunks_with_page.append((chunk, page_number))
    return chunks_with_page, {
        "file_title": metadata.get("title"),
        "authors": metadata.get("author"),
        "keywords": metadata.get("keywords"),
        "creation_date": metadata.get("creationDate")
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
def ingest_folder_to_qdrant(folder_path: str, qdrant_url: str, qdrant_api_key: str, collection_name: str, config):
    # if not HUGGINGFACE_API_TOKEN:
    #     raise ValueError("Missing HUGGINGFACE_API_TOKEN in .env")

    # Use HuggingFaceHub directly
    # embedding_model = HFCLIPTextEmbedding(
    #     model_name="sentence-transformers/all-MiniLM-L6-v2",
    #     api_token=HUGGINGFACE_API_TOKEN
    # )

    
    # Initialize embedding model using remote API
    embedding_model = RemoteEmbeddingsAPI(endpoint_url=EMBEDDING_API_URL)  

    qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    if not qdrant_client.collection_exists(collection_name=collection_name):
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )

    # Create metadata indexes
    for field in ["file_hash", "file_name", "file_title", "authors", "keywords", "creation_date", "page_number"]:
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

        texts = [chunk for chunk, _ in chunks_with_meta]
        page_numbers = [page for _, page in chunks_with_meta]

        vectors = embedding_model.embed_documents(texts)

        chunk_lengths = [len(c) for c in texts]
        print(f"   - {len(texts)} chunks extracted")
        print(f"→ Min: {min(chunk_lengths)}, Max: {max(chunk_lengths)}, Median: {int(statistics.median(chunk_lengths))}")

        points = []
        for chunk, vec, page_num in zip(texts, vectors, page_numbers):
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
                    "page_number": str(page_num),
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





# # === Text Extraction ===
# def get_pdf_text(filepath):
#     """
#     Extract text from a PDF file using PyMuPDF.
#     Args:
#         filepath (str): Path to the PDF file.
#     Returns:
#         str: Extracted text from the PDF.
#     """
#     text = ""
#     with pymupdf.open(filepath) as doc:
#         for page in doc:
#             text += page.get_text()
#     return text





# # === Main Ingestion ===
# def ingest_folder_to_qdrant(folder_path, qdrant_url, qdrant_api_key, collection_name):
#     # Set up embedding model and Qdrant vector store

#     # Ensure Hugging Face API token is set
#     if 'HUGGINGFACE_API_TOKEN' not in os.environ:
#         raise ValueError("Please set the HUGGINGFACE_API_TOKEN environment variable")

#     # embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

#     # Use HuggingFaceHub directly
#     embedding_model = HFCLIPTextEmbedding(
#         model_name="sentence-transformers/all-MiniLM-L6-v2",
#         api_token=os.environ['HUGGINGFACE_API_TOKEN']
#     )  

#     qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

#     # # Create collection if it doesn't exist
#     # vectorstore = Qdrant.from_texts(
#     #     texts=[],  # Empty init
#     #     embedding=embedding_model,
#     #     url=qdrant_url,
#     #     collection_name=collection_name,
#     #     api_key=qdrant_api_key,
#     #     prefer_grpc=True,
#     # )

#     # Create collection only if it doesn't exist
#     if not qdrant_client.collection_exists(collection_name=collection_name):
#         qdrant_client.create_collection(
#             collection_name=collection_name,
#             vectors_config=VectorParams(size=384, distance=Distance.COSINE)
#         )    

#     # Create payload indexes
#     qdrant_client.create_payload_index(
#         collection_name=collection_name,
#         field_name="file_hash",
#         field_schema=PayloadSchemaType.KEYWORD
#     )

#     qdrant_client.create_payload_index(
#         collection_name=collection_name,
#         field_name="file_name",
#         field_schema=PayloadSchemaType.KEYWORD
#     )

#     # vectorstore = Qdrant(
#     #     client=qdrant_client,
#     #     collection_name=collection_name,
#     #     embeddings=embedding_model
#     # )    

#     for filename in os.listdir(folder_path):
#         if not filename.lower().endswith(".pdf"):
#             continue

#         filepath = os.path.join(folder_path, filename)
#         file_hash = get_file_hash(filepath)

#         # Check if hash already in Qdrant
#         existing = qdrant_client.scroll(
#             collection_name=collection_name,
#             scroll_filter={
#                 "must": [{"key": "file_hash", "match": {"value": file_hash}}]
#             },
#             limit=1
#         )
#         # existing = qdrant_client.scroll(
#         #     collection_name=collection_name,
#         #     scroll_filter=Filter(
#         #         must=[
#         #             FieldCondition(
#         #                 key="file_hash",
#         #                 match=MatchValue(value=file_hash)
#         #             )
#         #         ]
#         #     ),
#         #     limit=1
#         # )
#         # print(f"Scroll result for {filename} (hash: {file_hash}): {existing}")

#         if existing[0]:
#             print(f"✔ Skipping (already indexed): {filename}")
#             continue

#         print(f"→ Processing: {filename}")
#         text = get_pdf_text(filepath)
#         chunks = get_text_chunks_recursive(text)
#         chunk_lengths = [len(chunk) for chunk in chunks]
#         print(f"   - {len(chunks)} chunks extracted")
#         print(f"→ Min: {min(chunk_lengths)}, Max: {max(chunk_lengths)}, Median: {int(statistics.median(chunk_lengths))}")

#         # Add chunks with metadata
#         # vectorstore.add_texts(
#         #     texts=chunks,
#         #     metadatas=[{
#         #         "file_name": filename,
#         #         "file_hash": file_hash
#         #     }] * len(chunks)
#         # )

#         vectors = embedding_model.embed_documents(chunks)

#         qdrant_client.upsert(
#             collection_name=collection_name,
#             points=[
#                 PointStruct(
#                     id=str(uuid.uuid4()),
#                     vector=vec,
#                     payload={
#                         "file_name": filename,
#                         "file_hash": file_hash,
#                         "text": chunk  # or rename to page_content if needed
#                     }
#                 )
#                 for chunk, vec in zip(chunks, vectors)
#             ]
#         )

#         print(f"✅ Indexed: {filename}")

#         points, _ = qdrant_client.scroll(collection_name=collection_name, limit=3)
#         for pt in points:
#             print(f"Payload: {pt.payload}")


# === Run ===
if __name__ == "__main__":
    ingest_folder_to_qdrant(
        folder_path=PDF_FOLDER,
        qdrant_url=QDRANT_URL,
        qdrant_api_key=QDRANT_API_KEY,
        collection_name=COLLECTION_NAME,
        config=config
    )
