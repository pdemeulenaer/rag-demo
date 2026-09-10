from fastapi import APIRouter, HTTPException
from typing import Literal
from collections import Counter
from sqlalchemy.exc import SQLAlchemyError

from src.api.papers.catalogue import Catalogue, snapshot_id
from src.api.papers.settings import PaperSettings

router = APIRouter()


def active_corpus(source="arxiv"):
    settings = PaperSettings()
    catalogue = Catalogue(settings.PAPERS_DATABASE_URL)
    try:
        from src.api.core.config import config
        catalogue.require_schema()
        active = catalogue.active(settings, source=source,
            collection=config.QDRANT_COLLECTION_NAME if source == "uploads" else settings.PAPERS_COLLECTION)
        return settings, active, snapshot_id(active)
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(503, "Paper catalogue unavailable; start PostgreSQL and run papers init-db") from exc
    finally:
        catalogue.close()


def inventory_response(source="all"):
    catalogue = Catalogue(PaperSettings().PAPERS_DATABASE_URL)
    try:
        catalogue.require_schema()
        documents = catalogue.inventory(source)
        counts = dict(Counter(row["status"] for row in documents))
        return {"source": source, "total_documents": len(documents),
                "queryable_documents": sum(row["queryable"] for row in documents),
                "status_counts": counts, "documents": documents,
                "titles": [row["title"] for row in documents if row["queryable"]]}
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(503, "Catalogue unavailable or outdated; start PostgreSQL and run make papers-init-db") from exc
    finally:
        catalogue.close()


@router.get("/catalogue")
def inventory(source: Literal["all", "uploads", "arxiv"] = "all"):
    return inventory_response(source)


@router.get("/papers")
def list_papers():
    settings, active, snapshot = active_corpus()
    return {"categories": settings.categories, "topic_terms": settings.terms,
            "corpus_snapshot": snapshot, "total_documents": len(active),
            "titles": [b["metadata"]["title"] for b in active],
            "papers": [{"paper_id": b["paper_id"], "build_id": b["id"],
                        **b["metadata"]} for b in active]}
