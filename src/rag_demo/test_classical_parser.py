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

from utils import (
    load_config,
    RemoteEmbeddingsAPI,
)

load_dotenv()
config = load_config()

# ---------- Configuration ----------
PDF_PATH = "/home/philippe/Documents/Github/rag-demo/src/rag_demo/folder/aa20674-12.pdf"
OUTPUT_FILE = "structured_output.md"


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


chunks, metadata = extract_chunks_with_metadata(PDF_PATH, config)
for chunk, page in chunks:
    print(f"Page {page}: {chunk}...")
print("Metadata:", metadata)

# # ---------- Run Pipeline ----------
# if __name__ == "__main__":
#     print(f"📄 Extracting text from: {PDF_PATH}")
#     raw_text = extract_pdf_text(PDF_PATH)

#     print("🚀 Sending text to Groq for processing...")
#     markdown_output = call_llm_for_structured_chunks(raw_text)

#     with open("structured_output_raw.md", "w", encoding="utf-8") as f:
#         f.write(raw_text)

#     with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
#         f.write(markdown_output)

#     print(f"✅ Markdown output written to: {OUTPUT_FILE}")    