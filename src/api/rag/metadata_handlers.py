# src/api/rag/metadata_handlers.py
import logging
import re
import unicodedata
from qdrant_client import QdrantClient
from src.api.core.config import config

logger = logging.getLogger(__name__)


qc = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY)
COLL = config.QDRANT_COLLECTION_NAME

def _normalize(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", errors="ignore").decode()
    s = re.sub(r"[^\w\s]", " ", s)    # remove punctuation
    return " ".join(s.lower().split())

def _last_name(s: str) -> str:
    ns = _normalize(s)
    parts = ns.split()
    return parts[-1] if parts else ""

def list_titles():
    logger.debug("Fetching list of titles from Qdrant")
    r, _ = qc.scroll(collection_name=COLL, limit=10000)
    titles = sorted({p.payload.get("file_title") for p in r if p.payload.get("file_title")})
    logger.info("Found %d unique titles", len(titles))
    return titles

def list_authors():
    r, _ = qc.scroll(collection_name=COLL, limit=10000)
    authors = set()
    for p in r:
        for a in p.payload.get("authors", []):
            authors.add(a)
    return sorted(authors)

# def titles_by_author(author, year=None):
#     must = [{"key": "authors", "match": {"value": author}}]
#     if year:
#         must.append({"key": "year", "match": {"value": year}})
#     r, _ = qc.scroll(collection_name=COLL, scroll_filter={"must": must}, limit=10000)
#     return sorted({p.payload.get("file_title") for p in r if p.payload.get("file_title")})
def titles_by_author(author: str | None, year: str | None = None):
    if not author:
        logger.info("titles_by_author called without author; returning empty list")
        return []

    author = author.strip()
    logger.info("titles_by_author: requested author=%s year=%s", author, year)

    # 1) Try strict keyword match on authors payload (best when ingestion is clean)
    must = [{"key": "authors", "match": {"value": author}}]
    if year:
        must.append({"key": "year", "match": {"value": str(year)}})

    try:
        r, _ = qc.scroll(collection_name=COLL, scroll_filter={"must": must}, limit=10000)
        titles = {p.payload.get("file_title") for p in r if p.payload.get("file_title")}
        if titles:
            logger.info("titles_by_author: strict match found %d titles", len(titles))
            return sorted(titles)
    except Exception as e:
        logger.exception("titles_by_author: strict scroll failed: %s", e)

    # 2) Fallback: scan collection and do tolerant last-name matching
    logger.info("titles_by_author: strict match returned nothing, running fallback scan")
    try:
        r, _ = qc.scroll(collection_name=COLL, limit=10000)
    except Exception as e:
        logger.exception("titles_by_author: full scroll failed: %s", e)
        return []

    query_last = _last_name(author)
    logger.debug("titles_by_author: normalized last name = '%s'", query_last)

    matched = set()
    for p in r:
        payload = p.payload or {}
        # optional: check year
        if year and str(payload.get("year")) != str(year):
            continue

        authors = payload.get("authors", []) or []
        # authors could be a string or list
        if isinstance(authors, str):
            authors_list = [authors]
        else:
            authors_list = list(authors)

        # join authors and normalize
        authors_joined = " ".join(authors_list)
        if query_last and query_last in _normalize(authors_joined):
            title = payload.get("file_title")
            if title:
                matched.add(title)

    logger.info("titles_by_author: fallback matched %d titles", len(matched))
    return sorted(matched)

def author_of_title(title):
    r, _ = qc.scroll(collection_name=COLL,
                     scroll_filter={"must":[{"key":"file_title","match":{"value":title}}]},
                     limit=1)
    return r[0].payload.get("authors") if r else []

def summarize_paper(title):
    r, _ = qc.scroll(collection_name=COLL,
                     scroll_filter={"must":[{"key":"file_title","match":{"value":title}}]},
                     limit=10000)
    if not r:
        return f"No paper titled '{title}' found."
    # if you stored per-chunk summary, use it directly
    chunk_summaries = [p.payload.get("summary") for p in r if p.payload.get("summary")]
    if chunk_summaries:
        return "\n".join(chunk_summaries)
    # fallback: combine full text and call your summarizer_llm
    full_text = "\n\n".join(p.payload["text"] for p in r)
    # call summarizer LLM (you already have summarizer_llm in main code)
    return full_text
