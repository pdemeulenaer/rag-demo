# src/api/rag/metadata_handlers.py
import logging
import re
import unicodedata
from qdrant_client import QdrantClient
from src.api.core.config import config

logger = logging.getLogger(__name__)


qc = QdrantClient(
    url=config.QDRANT_URL,
    port=config.qdrant_port,
    api_key=config.QDRANT_API_KEY,
)
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

def titles_by_author(author: str | None, year: str | None = None):
    """
    Return a sorted list like:
       "Title, A. Author, B. Coauthor (2023)"
       or "Title, FirstAuthor et al. (2023)"
    """

    if not author:
        return []

    author_norm = _normalize(author)
    parts = author_norm.split()
    q_last = parts[-1] if parts else ""
    q_first = parts[0] if len(parts) > 1 else ""

    def format_entry(p):
        payload = p.payload or {}
        title = payload.get("file_title") or payload.get("title")
        if not title:
            return None
        authors = payload.get("authors") or []
        if isinstance(authors, str):
            # split on common separators
            for sep in [";", " and ", ","]:
                if sep in authors:
                    authors = [a.strip() for a in authors.split(sep) if a.strip()]
                    break
            else:
                authors = [authors.strip()]
        if not authors:
            auth_str = "Unknown author"
        elif len(authors) > 3:
            auth_str = f"{authors[0]} et al."
        else:
            auth_str = ", ".join(authors)
        y = str(payload.get("year") or "n.d.")
        return f"{title}, {auth_str} ({y})"

    matched = set()

    # --- strict filter first ---
    must = [{"key": "authors", "match": {"value": author}}]
    if year:
        must.append({"key": "year", "match": {"value": str(year)}})
    try:
        r, _ = qc.scroll(collection_name=COLL, scroll_filter={"must": must}, limit=10_000)
        matched |= {fmt for p in r if (fmt := format_entry(p))}
    except Exception as e:
        logger.warning("strict scroll failed: %s", e)

    # --- fallback scan for last-name + optional first-name/initial ---
    try:
        r, _ = qc.scroll(collection_name=COLL, limit=10_000)
    except Exception as e:
        logger.warning("full scan failed: %s", e)
        return sorted(matched)

    for p in r:
        payload = p.payload or {}
        if year and str(payload.get("year")) != str(year):
            continue
        authors = payload.get("authors") or []
        if isinstance(authors, str):
            authors = [authors]
        for a in authors:
            a_norm = _normalize(a)
            a_parts = a_norm.split()
            if not a_parts:
                continue
            a_first, a_last = a_parts[0], a_parts[-1]
            if q_last and q_last in a_last:
                if not q_first or q_first == a_first or q_first[0] == a_first[0]:
                    if fmt := format_entry(p):
                        matched.add(fmt)
                    break

    return sorted(matched)


def author_of_title(title):
    r, _ = qc.scroll(collection_name=COLL,
                     scroll_filter={"must":[{"key":"file_title","match":{"value":title}}]},
                     limit=1)
    return r[0].payload.get("authors") if r else []

# def summarize_paper(title):
#     r, _ = qc.scroll(collection_name=COLL,
#                      scroll_filter={"must":[{"key":"file_title","match":{"value":title}}]},
#                      limit=10000)
#     if not r:
#         return f"No paper titled '{title}' found."
#     # if you stored per-chunk summary, use it directly
#     chunk_summaries = [p.payload.get("summary") for p in r if p.payload.get("summary")]
#     if chunk_summaries:
#         return "\n".join(chunk_summaries)
#     # fallback: combine full text and call your summarizer_llm
#     full_text = "\n\n".join(p.payload["text"] for p in r)
#     # call summarizer LLM (you already have summarizer_llm in main code)
#     return full_text

def summarize_paper(title):
    """
    Retrieves the full document summary for a paper identified by its title.
    It leverages the dedicated 'type="summary"' field in the payload.
    """
    logger.info(f"Attempting to retrieve full document summary (type=summary) for title: '{title}'")

    # Define the precise filter using the dedicated 'type' field:
    must_filter = [
        {"key": "file_title", "match": {"value": title}},
        # ✅ New, explicit filter for the document summary point
        {"key": "type", "match": {"value": "summary"}}
    ]
    
    try:
        # We only need one point (the document summary point)
        r, _ = qc.scroll(
            collection_name=COLL,
            scroll_filter={"must": must_filter},
            limit=1
        )
    except Exception as e:
        logger.error("Qdrant scroll failed during summarize_paper: %s", e)
        return f"Error retrieving summary for '{title}' due to a database issue."

    if not r:
        logger.warning(f"No document summary point (type=summary) found for title: '{title}'")
        return f"No full document summary found for the paper titled '{title}'."

    # The point's 'text' payload contains the full text used for embedding, 
    # which includes the header and the LLM-generated summary string.
    full_text_payload = r[0].payload.get("text")
    
    if full_text_payload:
        # The text field contains the header and the summary.
        # We want to return *only* the summary content to the user.
        # Since the header ends with "Summary text: \n", we can split the string.
        
        # Define the header marker used in ingestion
        SUMMARY_MARKER = "Summary text: \n"
        
        # Find the content after the marker
        if SUMMARY_MARKER in full_text_payload:
            # Split the string once by the marker and take the second part (the summary content)
            summary_content = full_text_payload.split(SUMMARY_MARKER, 1)[-1].strip()
            return summary_content
        else:
            # Fallback to returning the whole text if the marker wasn't found (unlikely)
            return full_text_payload
            
    return f"Full document summary point found for '{title}', but the content was empty."
