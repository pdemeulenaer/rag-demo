from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from src.api.papers.catalogue import Catalogue, snapshot_id
from src.api.papers.settings import PaperSettings

router = APIRouter()


def active_corpus():
    settings = PaperSettings()
    catalogue = Catalogue(settings.PAPERS_DATABASE_URL)
    try:
        active = catalogue.active(settings)
        return settings, active, snapshot_id(active)
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Paper catalogue unavailable; start PostgreSQL and run papers init-db") from exc
    finally:
        catalogue.close()


@router.get("/papers")
def list_papers():
    settings, active, snapshot = active_corpus()
    return {"categories": settings.categories, "topic_terms": settings.terms,
            "corpus_snapshot": snapshot, "total_documents": len(active),
            "titles": [b["metadata"]["title"] for b in active],
            "papers": [{"paper_id": b["paper_id"], "build_id": b["id"],
                        **b["metadata"]} for b in active]}
