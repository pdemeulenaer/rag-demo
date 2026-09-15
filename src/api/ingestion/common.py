# src/api/ingestion/common.py
from typing import Literal
# from src.api.ingestion.ingest_documents import AdditionalMetadata #problem: circular import
from typing import Literal, Any

def build_point_payload(
    *,
    file_name: str,
    file_hash: str,
    doc_meta: Any, #AdditionalMetadata,
    text: str,
    point_type: Literal["chunk", "summary", "figure"],
    img_caption: str | None = None,
    img_page: int | None = None,
    img_path: str | None = None,
) -> dict:
    """
    Returns a payload dict that is **identical** for both the real‑time
    and batch ingestion flows.  All document‑level fields (title,
    authors, keywords, year) are always present, making downstream
    consumers agnostic to the ingestion mode.
    """
    payload = {
        "file_name": file_name,
        "file_hash": file_hash,
        "file_title": doc_meta.title,
        "authors": doc_meta.authors,
        "keywords": doc_meta.keywords,
        "year": doc_meta.publication_year,
        "type": point_type,
        "text": text,
    }
    if img_caption is not None:
        payload["caption"] = img_caption
    if img_page is not None:
        payload["page"] = img_page
    if img_path is not None:
        payload["image_path"] = img_path
    return payload