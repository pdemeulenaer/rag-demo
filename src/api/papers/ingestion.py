from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

from .arxiv import Paper, matches_scope
from .consistency import activate_verified


def discover_daily(client, catalogue, settings):
    """Checkpoint only fully persisted pages; first response time avoids paging gaps."""
    count = 0
    sets = client.oai_sets(settings.categories)
    for category, spec in sets.items():
        key = f"oai:{settings.scope_id}:{category}"
        checkpoint = catalogue.checkpoint(key)
        since = (datetime.fromisoformat(checkpoint.replace("Z", "+00:00")) if checkpoint
                 else datetime.now(timezone.utc) - timedelta(days=settings.ARXIV_BACKFILL_DAYS))
        # Day granularity, including overlap, catches late publication and is replay-safe.
        since = (since - timedelta(days=1)).date().isoformat()
        first_response = None
        for response_date, records in client.changes(spec, since):
            if not response_date:
                raise ValueError("OAI response has no checkpoint timestamp")
            first_response = first_response or response_date
            selected = {}
            for record in records:
                if record["deleted"]:
                    catalogue.tombstone(record["id"])
                elif matches_scope(record["categories"], record["title"], record["abstract"], settings):
                    selected[record["id"]] = record
            identifiers = list(selected)
            for start in range(0, len(identifiers), 50):
                for paper in client.resolve(identifiers[start:start + 50]):
                    paper.license = selected[paper.arxiv_id]["license"]
                    if matches_scope(paper.categories, paper.title, paper.abstract, settings):
                        catalogue.discover(paper, settings)
                        count += 1
        if first_response:
            catalogue.set_checkpoint(key, first_response)
    return count


def extract_chunks(pdf, max_chunks):
    import pymupdf
    chunks = []
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        if document.is_encrypted:
            raise ValueError("Encrypted PDF is not supported")
        for page_number, page in enumerate(document, 1):
            content = page.get_text("text", sort=True).strip()
            for offset in range(0, len(content), 1600):
                chunk = content[offset:offset + 1800].strip()
                if chunk:
                    chunks.append({"page_number": page_number, "text": chunk})
                if len(chunks) > max_chunks:
                    raise ValueError("Paper exceeds configured chunk budget")
    if not chunks:
        raise ValueError("PDF has no extractable text; OCR is not part of this milestone")
    return chunks


class PaperIndexer:
    def __init__(self, settings, qdrant, embed):
        self.settings, self.qdrant, self.embed = settings, qdrant, embed

    def index(self, build, paper, chunks):
        from qdrant_client import models as m
        collection = self.settings.PAPERS_COLLECTION
        first_vector = self.embed([chunks[0]["text"]])[0]
        dimension = len(first_vector)
        if not self.qdrant.collection_exists(collection):
            self.qdrant.create_collection(collection, vectors_config=m.VectorParams(
                size=dimension, distance=m.Distance.COSINE))
        info = self.qdrant.get_collection(collection)
        if getattr(info.config.params.vectors, "size", None) != dimension:
            raise ValueError("Embedding dimension mismatch; use a new paper collection")
        self.qdrant.create_payload_index(collection, "build_id", m.PayloadSchemaType.KEYWORD, wait=True)
        self.qdrant.create_payload_index(collection, "text", m.TextIndexParams(
            type="text", tokenizer=m.TokenizerType.WORD, lowercase=True), wait=True)
        for start in range(0, len(chunks), 32):
            batch = chunks[start:start + 32]
            vectors = self.embed([c["text"] for c in batch])
            if len(vectors) != len(batch):
                raise ValueError("Embedding API returned an incomplete batch")
            points = []
            for offset, (chunk, vector) in enumerate(zip(batch, vectors)):
                points.append(m.PointStruct(
                    id=str(uuid5(NAMESPACE_URL, f"{build['id']}:{start + offset}")), vector=vector,
                    payload={**chunk, "type": "text", "build_id": build["id"],
                        "paper_id": build["paper_id"], "arxiv_id": paper.arxiv_id,
                        "paper_version": paper.version, "source_url": paper.source_url,
                        "file_title": paper.title, "authors": paper.authors,
                        "year": int(paper.published[:4]), "categories": paper.categories},
                ))
            self.qdrant.upsert(collection, points, wait=True)
        count = self.qdrant.count(collection, count_filter=m.Filter(must=[
            m.FieldCondition(key="build_id", match=m.MatchValue(value=build["id"]))
        ]), exact=True).count
        if count != len(chunks):
            raise ValueError(f"Index verification failed: expected {len(chunks)}, got {count}")


def process_pending(client, catalogue, settings, store, indexer, limit, selected_builds=None):
    completed, failed = 0, 0
    for build in (catalogue.pending(settings, limit) if selected_builds is None else selected_builds):
        catalogue.start(build["id"])
        try:
            paper = Paper(**build["metadata"])
            pdf = client.download_pdf(paper, settings.ARXIV_MAX_PDF_MB * 1024 * 1024)
            source = store.put(build["id"], "source.pdf", pdf)
            chunks = extract_chunks(pdf, settings.ARXIV_MAX_CHUNKS)
            text = store.put_json(build["id"], "chunks.json", chunks)
            metadata = store.put_json(build["id"], "metadata.json", paper.to_dict())
            indexer.index(build, paper, chunks)
            manifest = {"source": source, "text": text, "metadata": metadata,
                "chunk_count": len(chunks), "pipeline_id": settings.pipeline_id,
                "embedding_model": settings.EMBEDDING_MODEL, "collection": settings.PAPERS_COLLECTION}
            manifest["artifact"] = store.put_json(build["id"], "manifest.json", manifest)
            activate_verified(catalogue, indexer.qdrant, build, manifest)
            completed += 1
        except Exception as exc:
            # Do not store credentials/HTTP request details in status responses.
            catalogue.fail(build["id"], type(exc).__name__)
            failed += 1
    return {"completed": completed, "failed": failed}
