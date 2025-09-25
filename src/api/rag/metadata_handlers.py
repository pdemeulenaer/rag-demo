from qdrant_client import QdrantClient
from src.api.core.config import config

qc = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY)
COLL = config.QDRANT_COLLECTION_NAME

def list_titles():
    r, _ = qc.scroll(collection_name=COLL, limit=10000)
    return sorted({p.payload.get("file_title") for p in r if p.payload.get("file_title")})

def list_authors():
    r, _ = qc.scroll(collection_name=COLL, limit=10000)
    authors = set()
    for p in r:
        for a in p.payload.get("authors", []):
            authors.add(a)
    return sorted(authors)

def titles_by_author(author, year=None):
    must = [{"key": "authors", "match": {"value": author}}]
    if year:
        must.append({"key": "year", "match": {"value": year}})
    r, _ = qc.scroll(collection_name=COLL, scroll_filter={"must": must}, limit=10000)
    return sorted({p.payload.get("file_title") for p in r if p.payload.get("file_title")})

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
