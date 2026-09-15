"""PostgreSQL is the source of truth; Qdrant is a rebuildable projection.

SQLite is supported for isolated unit tests only. Production writers take a
PostgreSQL advisory lock for the entire discovery/processing command.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import (JSON, Column, ForeignKey, Integer, MetaData, String, Table, Text,
                        create_engine, insert, inspect, select, update, text)

from .arxiv import matches_scope

schema = MetaData()
papers = Table("papers", schema,
    Column("id", String, primary_key=True),
    Column("source_id", String, nullable=False, unique=True),
    Column("source", String, nullable=False, server_default="arxiv"),
    Column("active_build", String), Column("active_version", Integer, default=0),
    Column("metadata", JSON, nullable=False), Column("deleted", Integer, default=0))
versions = Table("paper_versions", schema,
    Column("id", String, primary_key=True), Column("paper_id", String, ForeignKey("papers.id"), nullable=False, index=True),
    Column("version", Integer, nullable=False), Column("metadata", JSON, nullable=False))
builds = Table("paper_builds", schema,
    Column("id", String, primary_key=True), Column("paper_id", String, ForeignKey("papers.id"), nullable=False, index=True),
    Column("version_id", String, ForeignKey("paper_versions.id"), nullable=False), Column("version", Integer, nullable=False),
    Column("pipeline_id", String, nullable=False), Column("collection", String, nullable=False),
    Column("embedding_model", String, nullable=False), Column("metadata", JSON, nullable=False),
    Column("status", String, nullable=False), Column("attempts", Integer, default=0),
    Column("error", Text), Column("manifest", JSON), Column("updated_at", String, nullable=False))
checkpoints = Table("paper_checkpoints", schema,
    Column("id", String, primary_key=True), Column("value", String, nullable=False))


def now():
    return datetime.now(timezone.utc).isoformat()


class Catalogue:
    def __init__(self, url):
        self.engine = create_engine(url, pool_pre_ping=True)

    def close(self):
        self.engine.dispose()

    def initialize(self):
        # Version 2 generalizes identity without replacing rows or rebuilding embeddings.
        if inspect(self.engine).has_table("paper_checkpoints"):
            current = self.checkpoint("schema_version")
            if current not in {None, "1", "2"}:
                raise RuntimeError("Unsupported paper catalogue schema version")
        if inspect(self.engine).has_table("papers"):
            columns = {c["name"] for c in inspect(self.engine).get_columns("papers")}
            with self.engine.begin() as connection:
                if "arxiv_id" in columns:
                    connection.execute(text("ALTER TABLE papers RENAME COLUMN arxiv_id TO source_id"))
                if "source" not in columns:
                    connection.execute(text("ALTER TABLE papers ADD COLUMN source VARCHAR NOT NULL DEFAULT 'arxiv'"))
        schema.create_all(self.engine)
        from .schedule_store import run_schema
        run_schema.create_all(self.engine)  # Additive; existing v2 API/worker remain compatible.
        self.set_checkpoint("schema_version", "2")

    def require_schema(self):
        if self.checkpoint("schema_version") != "2":
            raise RuntimeError("Catalogue needs migration: run make papers-init-db")

    @contextmanager
    def writer_lock(self):
        with self.engine.connect() as connection:
            postgres = self.engine.dialect.name == "postgresql"
            if postgres and not connection.execute(text("SELECT pg_try_advisory_lock(724192601)")).scalar():
                raise RuntimeError("Another paper ingestion command is running; retry later")
            try:
                yield
            finally:
                if postgres:
                    connection.execute(text("SELECT pg_advisory_unlock(724192601)"))

    def checkpoint(self, key):
        with self.engine.connect() as connection:
            return connection.execute(select(checkpoints.c.value).where(checkpoints.c.id == key)).scalar()

    def set_checkpoint(self, key, value):
        with self.engine.begin() as connection:
            if connection.execute(select(checkpoints.c.id).where(checkpoints.c.id == key)).first():
                connection.execute(update(checkpoints).where(checkpoints.c.id == key).values(value=value))
            else:
                connection.execute(insert(checkpoints).values(id=key, value=value))

    def discover(self, paper, settings):
        paper_id = str(uuid5(NAMESPACE_URL, f"https://arxiv.org/abs/{paper.arxiv_id}"))
        version_id = str(uuid5(NAMESPACE_URL, f"{paper_id}:v{paper.version}"))
        build_id = str(uuid5(NAMESPACE_URL, f"{version_id}:{settings.pipeline_id}"))
        metadata = paper.to_dict()
        with self.engine.begin() as connection:
            existing = connection.execute(select(papers).where(papers.c.id == paper_id)).mappings().first()
            if existing is None:
                connection.execute(insert(papers).values(id=paper_id, source_id=paper.arxiv_id, source="arxiv",
                    metadata=metadata, active_version=0, deleted=0))
            elif existing["metadata"]["version"] <= paper.version:
                connection.execute(update(papers).where(papers.c.id == paper_id).values(metadata=metadata, deleted=0))
            if connection.execute(select(versions.c.id).where(versions.c.id == version_id)).first():
                connection.execute(update(versions).where(versions.c.id == version_id).values(metadata=metadata))
            else:
                connection.execute(insert(versions).values(id=version_id, paper_id=paper_id,
                    version=paper.version, metadata=metadata))
            if not connection.execute(select(builds.c.id).where(builds.c.id == build_id)).first():
                connection.execute(insert(builds).values(id=build_id, paper_id=paper_id,
                    version_id=version_id, version=paper.version, pipeline_id=settings.pipeline_id,
                    collection=settings.PAPERS_COLLECTION, embedding_model=settings.EMBEDDING_MODEL,
                    metadata=metadata, status="pending", attempts=0, updated_at=now()))
        return build_id

    def tombstone(self, arxiv_id):
        with self.engine.begin() as connection:
            connection.execute(update(papers).where(papers.c.source == "arxiv", papers.c.source_id == arxiv_id).values(deleted=1))

    def pending(self, settings, limit):
        # Caller holds writer_lock. Interrupted builds can be retried with the same IDs.
        with self.engine.connect() as connection:
            rows = connection.execute(select(builds).join(papers, builds.c.paper_id == papers.c.id).where(
                builds.c.status.in_(["pending", "failed", "running"]),
                builds.c.attempts < settings.ARXIV_MAX_ATTEMPTS,
                builds.c.pipeline_id == settings.pipeline_id, papers.c.deleted == 0,
                papers.c.source == "arxiv",
            ).order_by(builds.c.updated_at, builds.c.id)).mappings().all()
        return [dict(row) for row in rows if matches_scope(
            row["metadata"]["categories"], row["metadata"]["title"], row["metadata"]["abstract"], settings
        )][:limit]

    def start(self, build_id):
        with self.engine.begin() as connection:
            connection.execute(update(builds).where(builds.c.id == build_id).values(
                status="running", attempts=builds.c.attempts + 1, error=None, updated_at=now()))

    def fail(self, build_id, error):
        with self.engine.begin() as connection:
            connection.execute(update(builds).where(builds.c.id == build_id).values(
                status="failed", error=error, updated_at=now()))

    def activate(self, build, manifest):
        if manifest["chunk_count"] < 1:
            raise ValueError("Cannot activate an empty build")
        with self.engine.begin() as connection:
            metadata = connection.execute(select(builds.c.metadata).where(builds.c.id == build["id"])).scalar_one()
            connection.execute(update(builds).where(builds.c.id == build["id"]).values(
                status="ready", manifest=manifest, error=None, updated_at=now()))
            # A retry of an old version must never replace an already active newer one.
            connection.execute(update(papers).where(papers.c.id == build["paper_id"],
                papers.c.active_version <= build["version"]).values(
                    active_build=build["id"], active_version=build["version"]))
            # arXiv's paper metadata may already describe a newer discovered version.
            # Only uploads replace their initial filename with extracted metadata here.
            connection.execute(update(papers).where(papers.c.id == build["paper_id"],
                papers.c.source == "uploads", papers.c.active_build == build["id"]).values(metadata=metadata))

    def active(self, settings, source="arxiv", collection=None):
        with self.engine.connect() as connection:
            rows = connection.execute(select(builds).join(papers, papers.c.active_build == builds.c.id).where(
                papers.c.deleted == 0, builds.c.status == "ready",
                papers.c.source == source,
                builds.c.collection == (collection or settings.PAPERS_COLLECTION),
                builds.c.embedding_model == settings.EMBEDDING_MODEL,
            ).order_by(builds.c.id)).mappings().all()
        return [dict(row) for row in rows if source != "arxiv" or matches_scope(
            row["metadata"]["categories"], row["metadata"]["title"], row["metadata"]["abstract"], settings)]

    def get_build(self, build_id):
        with self.engine.connect() as connection:
            row = connection.execute(select(builds).where(builds.c.id == build_id)).mappings().first()
            return dict(row) if row else None

    def upload(self, source_id, metadata, collection, embedding_model, pipeline_id):
        """Register immutable upload content; caller holds writer_lock."""
        paper_id = str(uuid5(NAMESPACE_URL, f"upload:{source_id}"))
        version_id = str(uuid5(NAMESPACE_URL, f"{paper_id}:v1"))
        build_id = str(uuid5(NAMESPACE_URL, f"{version_id}:{collection}:{pipeline_id}"))
        with self.engine.begin() as connection:
            if not connection.execute(select(papers.c.id).where(papers.c.id == paper_id)).first():
                connection.execute(insert(papers).values(id=paper_id, source="uploads", source_id=f"upload:{source_id}",
                    metadata=metadata, active_version=0, deleted=0))
                connection.execute(insert(versions).values(id=version_id, paper_id=paper_id, version=1, metadata=metadata))
            if not connection.execute(select(builds.c.id).where(builds.c.id == build_id)).first():
                connection.execute(insert(builds).values(id=build_id, paper_id=paper_id, version_id=version_id,
                    version=1, pipeline_id=pipeline_id, collection=collection, embedding_model=embedding_model,
                    metadata=metadata, status="pending", attempts=0, updated_at=now()))
        return self.get_build(build_id)

    def update_build(self, build_id, **values):
        with self.engine.begin() as connection:
            connection.execute(update(builds).where(builds.c.id == build_id).values(**values, updated_at=now()))

    def all_builds(self):
        with self.engine.connect() as connection:
            return [dict(row) for row in connection.execute(select(
                builds, papers.c.source, papers.c.source_id, papers.c.active_build, papers.c.deleted,
            ).join(papers, builds.c.paper_id == papers.c.id)).mappings()]

    def inventory(self, source="all"):
        """One row per document, exposing latest attempt and active revision separately."""
        grouped = {}
        for build in self.all_builds():
            if not build["deleted"] and (source == "all" or source == build["source"]):
                grouped.setdefault(build["paper_id"], []).append(build)
        result = []
        for paper_id, history in grouped.items():
            latest = max(history, key=lambda b: (b["version"], b["updated_at"], b["id"]))
            active = next((b for b in history if b["id"] == b["active_build"] and b["status"] == "ready"), None)
            meta = (active or latest)["metadata"]
            result.append({"paper_id": paper_id, "source": latest["source"], "source_id": latest["source_id"],
                "title": meta.get("title") or meta.get("file_name") or "Untitled",
                "status": latest["status"], "queryable": active is not None,
                "active_build": active["id"] if active else None,
                "active_version": active["version"] if active else None,
                "latest_build": latest["id"], "collection": (active or latest)["collection"],
                "expected_points": ((active or latest).get("manifest") or {}).get("chunk_count"),
                "error": latest["error"], "attempts": latest["attempts"]})
        return sorted(result, key=lambda row: (row["source"], row["title"]))

    def status(self):
        with self.engine.connect() as connection:
            return [dict(row) for row in connection.execute(select(
                builds.c.id, builds.c.version, builds.c.status, builds.c.attempts,
                builds.c.error, builds.c.updated_at)).mappings()]


def snapshot_id(active_builds):
    return hashlib.sha256(json.dumps(sorted(b["id"] for b in active_builds)).encode()).hexdigest()[:20]
