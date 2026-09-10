"""Run with python -m src.api.papers --help. Nothing is scheduled implicitly."""
import argparse
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json

from .arxiv import ArxivClient
from .catalogue import Catalogue
from .settings import PaperSettings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["scope", "init-db", "backfill", "sync", "process", "daily", "status", "audit", "import-uploads"])
    parser.add_argument("--legacy-embedding-model", help="Required for import-uploads: explicitly confirm the model used for existing vectors")
    parser.add_argument("--days", type=int, help="Backfill lookback; default ARXIV_BACKFILL_DAYS")
    parser.add_argument("--until", type=datetime.fromisoformat, help="Backfill end in ISO format (UTC)")
    parser.add_argument("--limit", type=int, help="Maximum PDFs processed in this invocation")
    parser.add_argument("--dry-run", action="store_true", help="Backfill only: display matching metadata without database writes")
    args = parser.parse_args()
    settings = PaperSettings()
    if args.dry_run and args.command != "backfill":
        parser.error("--dry-run is supported only for backfill")
    if args.days is not None and not 1 <= args.days <= 365:
        parser.error("--days must be between 1 and 365")
    if args.limit is not None and not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")
    if args.command == "import-uploads" and not args.legacy_embedding_model:
        parser.error("import-uploads requires --legacy-embedding-model (old uploader default: text-embedding-3-small)")
    if args.command == "scope":
        print(json.dumps({"categories": settings.categories, "topic_terms": settings.terms,
                          "scope_id": settings.scope_id}, indent=2))
        return
    if args.command == "status":
        catalogue = Catalogue(settings.PAPERS_DATABASE_URL)
        try:
            catalogue.require_schema()
            print(json.dumps({"documents": catalogue.inventory(), "builds": catalogue.status()}, indent=2))
        finally:
            catalogue.close()
        return
    if args.command in {"audit", "import-uploads"}:
        from src.api.core.config import config
        from .uploads import qdrant_client
        from .consistency import audit, import_uploads
        catalogue = Catalogue(settings.PAPERS_DATABASE_URL)
        try:
            catalogue.require_schema()
            with closing(qdrant_client()) as qdrant:
                if args.command == "audit":
                    result = audit(catalogue, qdrant, [settings.PAPERS_COLLECTION, config.QDRANT_COLLECTION_NAME])
                else:
                    with catalogue.writer_lock():
                        result = import_uploads(catalogue, qdrant, config.QDRANT_COLLECTION_NAME, args.legacy_embedding_model)
                print(json.dumps(result, indent=2))
                if args.command == "audit" and not result["ok"]:
                    raise SystemExit(1)
        finally:
            catalogue.close()
        return
    client = ArxivClient(settings.ARXIV_USER_AGENT)
    catalogue = None
    try:
        if args.dry_run:
            until = args.until or datetime.now(timezone.utc)
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            until = until.astimezone(timezone.utc)
            since = until - timedelta(days=args.days or settings.ARXIV_BACKFILL_DAYS)
            for paper in client.backfill(settings, since, until):
                print(json.dumps(paper.to_dict(), ensure_ascii=False))
            return
        catalogue = Catalogue(settings.PAPERS_DATABASE_URL)
        with catalogue.writer_lock():
            if args.command == "init-db":
                catalogue.initialize()
                print("Paper catalogue schema initialized")
                return
            catalogue.require_schema()
            if args.command == "backfill":
                until = args.until or datetime.now(timezone.utc)
                if until.tzinfo is None:
                    until = until.replace(tzinfo=timezone.utc)
                until = until.astimezone(timezone.utc)
                since = until - timedelta(days=args.days or settings.ARXIV_BACKFILL_DAYS)
                count = 0
                for paper in client.backfill(settings, since, until):
                    catalogue.discover(paper, settings)
                    count += 1
                print(json.dumps({"discovered": count, "processed": 0}))
            if args.command in {"sync", "daily"}:
                from .ingestion import discover_daily
                print(json.dumps({"discovered": discover_daily(client, catalogue, settings)}))
            if args.command in {"process", "daily"}:
                from openai import OpenAI
                from qdrant_client import QdrantClient
                from src.api.core.config import config
                from .artifacts import ArtifactStore
                from .ingestion import PaperIndexer, process_pending
                if settings.PAPERS_COLLECTION == config.QDRANT_COLLECTION_NAME:
                    raise ValueError("PAPERS_COLLECTION must differ from the legacy upload collection")
                with OpenAI(api_key=config.OPENAI_API_KEY) as embeddings, closing(QdrantClient(
                    url=config.QDRANT_URL, port=config.qdrant_port, api_key=config.QDRANT_API_KEY or None,
                )) as qdrant:
                    def embed(texts):
                        result = embeddings.embeddings.create(input=texts, model=settings.EMBEDDING_MODEL)
                        return [item.embedding for item in sorted(result.data, key=lambda item: item.index)]
                    result = process_pending(client, catalogue, settings, ArtifactStore(settings),
                        PaperIndexer(settings, qdrant, embed), args.limit or settings.ARXIV_DAILY_LIMIT)
                    print(json.dumps(result))
                    if result["failed"]:
                        raise SystemExit(1)
    finally:
        client.close()
        if catalogue:
            catalogue.close()


if __name__ == "__main__":
    main()
