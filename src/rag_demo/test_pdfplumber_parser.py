import os
import httpx
import hashlib
import uuid
import pdfplumber
from langchain_community.document_loaders.parsers import PDFPlumberParser
from langchain_core.documents.base import Blob
from langchain.text_splitter import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance, PayloadSchemaType
from typing import List, Generator, Tuple, Dict
import re
from dotenv import load_dotenv
from utils import load_config, RemoteEmbeddingsAPI

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

# === Section Detection and Chunking ===
def extract_sections_with_metadata(filepath: str, config) -> Tuple[List[Tuple[str, int, str]], Dict[str, str]]:
    chunks_with_metadata = []
    parser = PDFPlumberParser(text_kwargs={"layout": True})  # Enable layout-aware parsing
    try:
        blob = Blob.from_path(filepath)
    except Exception as e:
        raise FileNotFoundError(f"Failed to load PDF file: {filepath}. Error: {str(e)}")

    # Parse the PDF
    documents = list(parser.lazy_parse(blob))
    if not documents:
        return [], {}

    # Extract document-level metadata
    doc_metadata = documents[0].metadata or {}

    # Initialize variables for section detection
    full_text = ""
    section_chunks = []
    current_section = {"title": "Unknown", "content": "", "start_page": 1}
    section_pattern = re.compile(
        r"^(Abstract|Introduction|Methods|Results|Discussion|Conclusion|References|Acknowledgements|Appendix)",
        re.IGNORECASE | re.MULTILINE
    )

    with pdfplumber.open(filepath) as pdf:
        for doc_idx, doc in enumerate(documents):
            page_number = doc.metadata.get("page", 1)
            page_text = doc.page_content
            if not page_text.strip():
                continue

            try:
                page = pdf.pages[page_number - 1]
                # Extract potential headings (font size > 12 or bold)
                chars = page.chars
                potential_headings = [
                    char["text"] for char in chars
                    if char.get("size", 0) > 12 or char.get("fontname", "").lower().find("bold") != -1
                ]
                page_headings = "".join(potential_headings).strip()

                # Extract tables
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines"
                })
                table_text = ""
                if tables:
                    table_text = "\n".join([" | ".join([str(cell) for cell in row]) for table in tables for row in table])
                    page_text += "\n\n[Table Content]\n" + table_text

                # Check for section headers
                matches = list(section_pattern.finditer(page_headings + "\n" + page_text))
                if matches:
                    # Finalize the previous section
                    if current_section["content"].strip():
                        section_chunks.append(current_section)
                    # Start new sections
                    for match in matches:
                        section_title = match.group(1).capitalize()
                        start_idx = match.start()
                        # Add content before the new section to the previous section
                        if start_idx > 0:
                            current_section["content"] += page_headings[:start_idx] + page_text[:start_idx]
                        # Start a new section
                        current_section = {
                            "title": section_title,
                            "content": page_headings[start_idx:] + page_text[start_idx:],
                            "start_page": page_number
                        }
                else:
                    # Append to current section
                    current_section["content"] += page_text + "\n"
            except IndexError:
                print(f"Warning: Page {page_number} not found in PDF. Skipping.")

        # Finalize the last section
        if current_section["content"].strip():
            section_chunks.append(current_section)

    # Chunk sections and associate with metadata
    for section in section_chunks:
        section_title = section["title"]
        section_content = section["content"].strip()
        start_page = section["start_page"]
        if not section_content:
            continue

        # Split large sections into smaller chunks if needed
        section_chunks_split = get_text_chunks_recursive(section_content, config)
        for chunk in section_chunks_split:
            chunks_with_metadata.append((chunk, start_page, section_title))

    # Format metadata
    extracted_metadata = {
        "file_title": doc_metadata.get("title", ""),
        "authors": doc_metadata.get("author", ""),
        "keywords": doc_metadata.get("keywords", ""),
        "creation_date": doc_metadata.get("creationDate", ""),
        "table_count": sum(len(page.extract_tables()) for page in pdf.pages)
    }

    return chunks_with_metadata, extracted_metadata

# Run the extraction
try:
    chunks, metadata = extract_sections_with_metadata(PDF_PATH, config)
    for chunk, page, section_title in chunks:
        print(f"Page {page}, Section {section_title}: {chunk[:100]}...")
    print("Metadata:", metadata)
except Exception as e:
    print(f"Error processing PDF: {str(e)}")