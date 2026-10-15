"""Approved-only immutable publications; PostgreSQL owns source eligibility.

No models, embeddings, global alias merging or runtime KG retrieval. Rebuild the
projection from authoritative checkpoints/review, never trust edited reviewed.json.
"""
from collections import Counter, defaultdict
from hashlib import sha256
import json

from .artifacts import load_paper
from .jobs import canonical, directory_lock, validated_snapshot
from . import review

WRITER_VERSION = "kg-publication-v1"


def identity(kind, *parts):
    return kind + ":" + sha256(canonical(parts).encode()).hexdigest()


def check_scope(plan, selected_papers, catalogue):
    """All selected sources must still be active, ready, undeleted and identical."""
    for paper in selected_papers:
        rows = catalogue.scoped_ready_builds(paper["collection"], [paper["build_id"]], active_only=True)
        if len(rows) != 1:
            raise ValueError("Publication source is no longer active/ready; refresh the frozen corpus and review")
        row = rows[0]
        artifact = (row.get("manifest") or {}).get("artifact") or {}
        if (str(row["id"]) != paper["build_id"] or str(row["paper_id"]) != paper["paper_id"]
                or row["source"] != paper["source"] or row["version"] != paper["version"]
                or row["collection"] != paper["collection"] or row["deleted"]
                or str(row["active_build"]) != paper["build_id"]
                or artifact.get("sha256") != plan["manifest_hashes"][paper["build_id"]]):
            raise ValueError("Publication source identity/version/manifest changed")


def build_payload(directory, settings, catalogue, reader, *, filename="review.json"):
    """Caller holds local directory and catalogue writer locks. No writes/services to Neo4j."""
    expected, validation, chunks = review._snapshot(directory)
    decisions = review._load(review._path(directory, filename), expected)
    report, _ = review._summary(decisions, validation, chunks)
    _, plan, _ = validated_snapshot(directory)
    approved = {e.record_id: e for e in decisions.entries if e.decision == "approved"}
    held = set(report["approved_but_dependency_held"])
    eligible = {key: entry for key, entry in approved.items() if key not in held}
    if not eligible:
        raise ValueError("Publication needs at least one eligible approved record")
    if len(eligible) > settings.KG_PUBLISH_MAX_RECORDS:
        raise ValueError("Publication exceeds KG_PUBLISH_MAX_RECORDS")
    # v1 review remains readable, but has not passed scientific role/quality checks.
    selected_chunks = [(point, saved) for point, saved in chunks
                       if any(r.id in eligible for r in [*saved.batch.entities, *saved.batch.observations, *saved.batch.relationships])]
    if any(saved.batch.schema_version == "scientific-kg-v1" for _, saved in selected_chunks):
        raise ValueError("Publication requires reviewed scientific schema v2/v3; v1 is validation-only")
    builds = {str(saved.batch.build_id) for _, saved in selected_chunks}
    selected_papers = [p for p in plan["papers"] if p["build_id"] in builds]
    check_scope(plan, selected_papers, catalogue)
    frozen = defaultdict(list)
    for chunk in plan["chunks"]:
        frozen[chunk["build_id"]].append(chunk)
    source_chunks = {}
    ordinals = {}
    for paper in selected_papers:
        full, digest = load_paper(paper, catalogue, reader)
        if digest != plan["manifest_hashes"][paper["build_id"]] or [c.model_dump(mode="json") for c in full] != frozen[paper["build_id"]]:
            raise ValueError("Publication frozen chunks differ from verified catalogue artifacts")
        for index, chunk in enumerate(full):
            source_chunks[str(chunk.point_id)] = chunk
            ordinals[str(chunk.point_id)] = index
    included_points = {point for point, _ in selected_chunks}
    content = dict(writer_version=WRITER_VERSION, graph_name=settings.KG_GRAPH_NAME,
        plan_id=plan["plan_id"], candidate_fingerprint=decisions.candidate_fingerprint,
        extraction_model=plan["model"], extraction_revision=plan["extraction_revision"],
        review_fingerprint=sha256(canonical(decisions.model_dump(mode="json")).encode()).hexdigest(),
        papers=[p | dict(manifest_sha256=plan["manifest_hashes"][p["build_id"]]) for p in selected_papers],
        chunks=[source_chunks[p].model_dump(mode="json") | dict(chunk_index=ordinals[p]) for p in sorted(included_points)],
        records=[entry.model_dump(mode="json") for _, entry in sorted(eligible.items())])
    if len(canonical(content).encode()) > settings.KG_PUBLISH_MAX_BYTES:
        raise ValueError("Publication exceeds KG_PUBLISH_MAX_BYTES")
    publication_id = identity("publication", content)
    nodes, edges = [], []

    def node(label, identifier, properties, owned=False):
        props = {k: v for k, v in (dict(id=identifier) | properties).items() if v is not None}
        if owned:
            props["publication_id"] = publication_id
        nodes.append(dict(label=label, id=identifier, properties=props))

    def edge(kind, start, end, properties=None, discriminator=""):
        props = dict(id=identity("edge", publication_id, kind, start, end, discriminator), publication_id=publication_id)
        props.update(properties or {})
        edges.append(dict(type=kind, start=start, end=end, properties=props))

    source_ids = {}
    for paper in content["papers"]:
        paper_id = identity("paper", paper["paper_id"])
        build_id = identity("build", paper["paper_id"], paper["build_id"], paper["collection"])
        source_ids[paper["build_id"]] = build_id
        node("KGPaper", paper_id, dict(paper_id=paper["paper_id"], source=paper["source"]))
        node("KGSourceBuild", build_id, dict(paper_id=paper["paper_id"], build_id=paper["build_id"],
            source=paper["source"], collection=paper["collection"], version=paper["version"],
            title=paper["title"], manifest_sha256=paper["manifest_sha256"]))
        edge("HAS_BUILD", publication_id, build_id)
        edge("OF_PAPER", build_id, paper_id)
    chunk_ids = {}
    for chunk in content["chunks"]:
        identifier = identity("chunk", chunk["collection"], chunk["point_id"])
        chunk_ids[chunk["point_id"]] = identifier
        node("KGChunk", identifier, chunk | dict(text_sha256=sha256(chunk["text"].encode()).hexdigest()))
        edge("HAS_CHUNK", source_ids[chunk["build_id"]], identifier)
    record_ids = {key: identity("record", publication_id, key) for key in eligible}
    for key, entry in sorted(eligible.items()):
        record = entry.record
        source = record["evidence"][0]
        label = {"entity": "KGEntity", "observation": "KGObservation", "relationship": "KGRelationship"}[entry.record_type]
        properties = {k: v for k, v in record.items() if k not in {"id", "subject_id", "object_id", "evidence"}}
        properties.update(record_id=key, record_type=entry.record_type, record_json=canonical(record),
            review_json=canonical({k: getattr(entry, k) for k in ("decision", "reviewer", "reason", "notes")}),
            paper_id=source["paper_id"], build_id=source["build_id"], collection=source["collection"],
            point_id=source["point_id"], source=source["source"])
        properties.update(extraction_model=content["extraction_model"], extraction_revision=content["extraction_revision"])
        identifier = record_ids[key]
        node(label, identifier, properties, owned=True)
        edge("INCLUDES", publication_id, identifier)
        edge("FROM_BUILD", identifier, source_ids[source["build_id"]])
        for index, evidence in enumerate(record["evidence"]):
            edge("SUPPORTED_BY", identifier, chunk_ids[evidence["point_id"]],
                 dict(quote=evidence["quote"], evidence_json=canonical(evidence)), discriminator=index)
        if entry.record_type == "observation":
            edge("HAS_OBSERVATION", record_ids[record["subject_id"]], identifier)
        elif entry.record_type == "relationship":
            edge("SUBJECT", identifier, record_ids[record["subject_id"]])
            edge("OBJECT", identifier, record_ids[record["object_id"]])
            edge(record["predicate"].upper(), record_ids[record["subject_id"]], record_ids[record["object_id"]],
                 dict(assertion_id=identifier, epistemic_status=record["epistemic_status"]), discriminator=key)
    # An id is immutable; duplicates are permitted only if exactly identical.
    unique = {}
    for row in nodes:
        if row["id"] in unique and unique[row["id"]] != row:
            raise ValueError("Conflicting publication node identity")
        unique[row["id"]] = row
    nodes = sorted(unique.values(), key=lambda n: n["id"])
    edges.sort(key=lambda r: r["properties"]["id"])
    manifest = {k: content[k] for k in ("writer_version", "graph_name", "plan_id", "candidate_fingerprint", "review_fingerprint",
                                     "extraction_model", "extraction_revision")}
    manifest.update(publication_id=publication_id, content_hash=sha256(canonical(content).encode()).hexdigest(),
        counts=dict(records=len(eligible), entities=sum(e.record_type == "entity" for e in eligible.values()),
                    observations=sum(e.record_type == "observation" for e in eligible.values()),
                    relationships=sum(e.record_type == "relationship" for e in eligible.values()),
                    papers=len(selected_papers), chunks=len(included_points), nodes=len(nodes), edges=len(edges)))
    return dict(id=publication_id, graph_name=settings.KG_GRAPH_NAME, manifest=manifest,
                nodes=nodes, edges=edges, papers=selected_papers, plan=plan,
                approved_but_dependency_held=sorted(held))


def run(directory, settings, catalogue, reader, *, action="preview", filename="review.json", store=None, expect_active=None):
    if action not in {"preview", "stage", "verify", "activate"}:
        raise ValueError("Unknown publication action")
    with directory_lock(directory), catalogue.writer_lock():
        payload = build_payload(directory, settings, catalogue, reader, filename=filename)
        result = dict(publication_id=payload["id"], graph_name=payload["graph_name"],
            counts=payload["manifest"]["counts"], approved_but_dependency_held=payload["approved_but_dependency_held"],
            catalogue_eligible=True, graph_ready=False, query_readiness="not_checked",
            model_calls=0, action=action)
        if action == "preview":
            return result | dict(database_writes=0)
        if store is None:
            raise ValueError("Neo4j store is required for publication")
        # The store invokes this inside the Neo4j transaction, before commit.
        recheck = lambda: check_scope(payload["plan"], payload["papers"], catalogue)
        if action == "stage":
            return result | store.stage(payload, recheck)
        if action == "verify":
            return result | store.verify(payload, recheck)
        return result | store.activate(payload, expect_active, recheck)
