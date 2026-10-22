"""Live KG selection: bounded SQL discovery -> explicit IDs -> immutable manifest.

No evaluation files, Qdrant, Neo4j, model calls or SQL writes. Selection is metadata;
full artifacts are independently verified by prepare/prepare-preview.
"""
from hashlib import sha256
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator
from sqlalchemy import and_, func, or_, select

from src.api.papers.arxiv import matches_scope
from src.api.papers.catalogue import builds, papers
from .contracts import Record, Text
from .jobs import canonical, directory_lock
from .preview import PilotSelection, SnapshotPaper


class SelectedPaper(SnapshotPaper):
    group: Text
    source_id: Text
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    text_chunk_count: int = Field(ge=1)


class CatalogueSelection(Record):
    schema_version: Literal["kg-catalogue-selection-v1"] = "kg-catalogue-selection-v1"
    scope: Literal["live_active_catalogue_selection"] = "live_active_catalogue_selection"
    selection_id: str
    corpus_fingerprint: str
    papers: list[SelectedPaper] = Field(min_length=1)

    @model_validator(mode="after")
    def identities(self):
        if len({p.paper_id for p in self.papers}) != len(self.papers) or len({p.build_id for p in self.papers}) != len(self.papers):
            raise ValueError("Selection contains duplicate paper/build identities")
        content = [p.model_dump(mode="json") for p in self.papers]
        digest = sha256(canonical(content).encode()).hexdigest()
        if self.selection_id != "kg-selection:"+digest or self.corpus_fingerprint != digest[:20]:
            raise ValueError("Selection integrity mismatch; create a new manifest with kg-select")
        return self


def _query(settings, *, source="arxiv", after=None, ids=None, term=None, limit=20):
    if source not in {"arxiv", "uploads", "all"}:
        raise ValueError("Source must be arxiv, uploads or all")
    sources = ("arxiv", "uploads") if source == "all" else (source,)
    # Active build PK join; no inventory()/all_builds() scan or OFFSET pagination.
    statement = select(papers.c.id.label("paper_id"), papers.c.source, papers.c.source_id,
        builds.c.id.label("build_id"), builds.c.collection, builds.c.version, builds.c.metadata,
        builds.c.manifest["artifact"]["sha256"].as_string().label("manifest_sha256"),
        builds.c.manifest["chunk_order"]["count"].as_integer().label("text_chunk_count"))
    statement = statement.select_from(papers.join(builds, and_(papers.c.active_build == builds.c.id,
                                                               builds.c.paper_id == papers.c.id)))
    statement = statement.where(papers.c.deleted == 0, builds.c.status == "ready",
        builds.c.embedding_model == settings.EMBEDDING_MODEL,
        or_(*(and_(papers.c.source == kind, builds.c.collection == (
            settings.PAPERS_COLLECTION if kind == "arxiv" else settings.QDRANT_COLLECTION_NAME)) for kind in sources)))
    if after:
        statement = statement.where(papers.c.id > str(UUID(str(after))))
    if ids is not None:
        statement = statement.where(papers.c.id.in_(ids))
    if term:
        if len(term) > 200:
            raise ValueError("Catalogue search term must be at most 200 characters")
        escaped = term.replace("/", "//").replace("%", "/%").replace("_", "/_")
        statement = statement.where(or_(
            builds.c.metadata["title"].as_string().ilike("%"+escaped+"%", escape="/"),
            builds.c.metadata["abstract"].as_string().ilike("%"+escaped+"%", escape="/")))
    return statement.order_by(papers.c.id).limit(limit)


def _supported(row, settings):
    meta = row["metadata"]
    if row["source"] == "arxiv" and not matches_scope(meta.get("categories", []),meta.get("title", ""),meta.get("abstract", ""),settings):
        return False
    return (isinstance(row["manifest_sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", row["manifest_sha256"])
        and type(row["text_chunk_count"]) is int and row["text_chunk_count"] > 0)


def _paper(row, group="catalogue-selection"):
    return SelectedPaper(paper_id=row["paper_id"],build_id=row["build_id"],source=row["source"],
        source_id=row["source_id"],collection=row["collection"],version=row["version"],
        title=row["metadata"].get("title") or row["metadata"].get("file_name") or "Untitled",
        group=group,manifest_sha256=row["manifest_sha256"],text_chunk_count=row["text_chunk_count"])


def browse(catalogue, settings, *, source="arxiv", term=None, after=None, limit=20):
    """Keyset pagination, fetching only bounded batches of active build metadata.

Topic eligibility reuses the exact ingestion filter after SQL title/abstract search.
A sparse filter can require multiple small SQL reads, but never a full in-memory corpus.
"""
    if not 1 <= limit <= 100:
        raise ValueError("Catalogue page size must be 1–100")
    found, cursor = [], after
    with catalogue.engine.connect() as connection:
        while len(found) <= limit:
            rows = list(connection.execute(_query(settings,source=source,term=term,after=cursor,limit=limit+1)).mappings())
            if not rows:
                break
            for row in rows:
                cursor = row["paper_id"]
                if _supported(row,settings):
                    found.append(_paper(row).model_dump(mode="json"))
                    if len(found) > limit:
                        break
            if len(rows) < limit+1:
                break
    return dict(source=source,term=term,scope="live_active_catalogue_metadata",papers=found[:limit],
        returned=len(found[:limit]),has_more=len(found)>limit,
        next_after=found[limit-1]["paper_id"] if len(found)>limit else None,
        artifacts_verified=False,model_calls=0,database_writes=0)


def _resolve(catalogue, settings, identifiers):
    with catalogue.engine.connect() as connection:
        rows = connection.execute(_query(settings,source="all",ids=identifiers,limit=len(identifiers)+1)).mappings()
        return {row["paper_id"]:_paper(row) for row in rows if _supported(row,settings)}


def select_papers(catalogue, settings, *, paper_ids=(), pilot_path=None):
    groups = {}
    if pilot_path is not None:
        pilot = PilotSelection.model_validate_json(Path(pilot_path).read_text(encoding="utf-8"))
        groups.update({str(p.paper_id):p.group for p in pilot.papers})
    for identifier in paper_ids:
        groups.setdefault(str(UUID(str(identifier))),"catalogue-selection")
    if not groups:
        raise ValueError("Select explicit --paper-id values and/or --include-pilot; no implicit all-corpus selection")
    if len(groups) > settings.KG_PREPARE_MAX_PAPERS:
        raise ValueError("Selection exceeds KG_PREPARE_MAX_PAPERS; use smaller named batches")
    resolved = _resolve(catalogue,settings,sorted(groups))
    missing = set(groups).difference(resolved)
    if missing:
        raise ValueError("Papers not eligible in current ready/active scope or missing structured manifest: "+", ".join(sorted(missing)))
    selected = [resolved[key].model_copy(update=dict(group=groups[key])) for key in sorted(groups)]
    content = [p.model_dump(mode="json") for p in selected]
    digest = sha256(canonical(content).encode()).hexdigest()
    return CatalogueSelection(selection_id="kg-selection:"+digest,corpus_fingerprint=digest[:20],papers=selected)


def check_current(document, catalogue, settings):
    if len(document.papers) > settings.KG_PREPARE_MAX_PAPERS:
        raise ValueError("Selection exceeds KG_PREPARE_MAX_PAPERS")
    current = _resolve(catalogue,settings,[str(p.paper_id) for p in document.papers])
    for frozen in document.papers:
        row = current.get(str(frozen.paper_id))
        if row is None or row.model_copy(update=dict(group=frozen.group)) != frozen:
            raise ValueError("KG selection is stale; paper/build/metadata/manifest changed. Select into a new KG_DIR.")


def load_selection(path):
    return CatalogueSelection.model_validate_json(Path(path).read_text(encoding="utf-8"))


def save_selection(document, path, catalogue, settings):
    """Never overwrite an existing selection or place a new one in an old extraction run."""
    path = Path(path)
    if path.name in {"plan.json","candidates.json","review.json","reviewed.json","failures.json","checkpoints.sqlite"}:
        raise ValueError("Selection filename conflicts with KG outputs")
    with directory_lock(path.parent):
        check_current(document,catalogue,settings)
        if path.exists():
            if load_selection(path) != document:
                raise ValueError("Existing selection differs; use a new KG_DIR/selection file")
        else:
            if (path.parent/"plan.json").exists():
                raise ValueError("Existing extraction run has no matching selection; use a new KG_DIR")
            # Publish complete bytes atomically, with exclusive creation (never replace).
            temporary = None
            try:
                with NamedTemporaryFile(mode="w",encoding="utf-8",dir=path.parent,delete=False) as handle:
                    temporary = Path(handle.name)
                    handle.write(canonical(document.model_dump(mode="json"))+"\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.link(temporary,path)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
    return dict(output=str(path),selection_id=document.selection_id,papers_selected=len(document.papers),
        metadata_text_chunks=sum(p.text_chunk_count for p in document.papers),artifacts_verified=False,
        model_calls=0,database_writes=0,papers=[p.model_dump(mode="json") for p in document.papers])
