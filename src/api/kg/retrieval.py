"""Read-only KG evidence retrieval. No extraction libraries, models or generated Cypher.

Hybrid chunks and exact reviewed name/alias mentions seed a bounded native traversal.
The result is always original source text, never an extracted assertion as evidence.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
import json
import re
import unicodedata

from src.api.rag.contracts import EvidenceChunk, FederatedRetrievalScope
from src.api.rag.tools.evidence import validate_target
from .contracts import SourceChunk
from .scientific_schema import Entity, Observation, Relationship

POLICY = "hybrid-reviewed-graph-v1"


class KGUnavailable(ValueError):
    """A safe public failure code; do not expose database exceptions or credentials."""


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def identity(kind, *parts):
    return kind + ":" + sha256(canonical(parts).encode()).hexdigest()


def normalized(value):
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", value).casefold()))


def mentioned(name, query):
    """Exact normalized, word-bounded mention; no alias inference or entity merging."""
    name = normalized(name)
    return len(name) >= 2 and f" {name} " in f" {normalized(query)} "


@dataclass
class GraphEvidence:
    chunks: list[EvidenceChunk]
    diagnostics: dict


class KGReader:
    def __init__(self, driver, settings):
        self.driver, self.settings = driver, settings

    @classmethod
    def connect(cls, settings):
        from neo4j import GraphDatabase
        return cls(GraphDatabase.driver(settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD.get_secret_value()),
            connection_timeout=settings.KG_NEO4J_TIMEOUT_SECONDS,
            max_transaction_retry_time=0), settings)

    def close(self):
        self.driver.close()

    @contextmanager
    def transaction(self):
        from neo4j import READ_ACCESS
        with self.driver.session(database=self.settings.NEO4J_DATABASE,
                                 default_access_mode=READ_ACCESS) as session:
            with session.begin_transaction(timeout=self.settings.KG_NEO4J_TIMEOUT_SECONDS) as tx:
                yield tx

    def _active(self, tx, expected=None):
        row = tx.run("MATCH (c:KGCorpus {name: $name}) "
            "MATCH (p:KGPublication {id: c.active_publication_id, graph_name: $name, status: 'active'}) "
            "RETURN p.id AS id, p.manifest_json AS manifest", name=self.settings.KG_GRAPH_NAME).single()
        if not row:
            raise KGUnavailable("kg_no_active_publication")
        expected = expected or self.settings.KG_QUERY_PUBLICATION_ID or None
        if expected and row["id"] != expected:
            raise KGUnavailable("kg_publication_changed")
        manifest = json.loads(row["manifest"])
        if (manifest["publication_id"] != row["id"] or manifest["writer_version"] != "kg-publication-v1"
                or manifest["graph_name"] != self.settings.KG_GRAPH_NAME):
            raise KGUnavailable("kg_invalid_publication")
        if manifest["counts"]["records"] > self.settings.KG_QUERY_MAX_RECORDS:
            raise KGUnavailable("kg_query_record_limit")
        return row["id"], manifest

    def publication(self, expected=None):
        with self.transaction() as tx:
            pub, manifest = self._active(tx, expected)
            return dict(publication_id=pub, graph_name=self.settings.KG_GRAPH_NAME,
                        policy=POLICY, manifest=manifest)

    def search(self, query, *, scope, catalogue, seeds, limit, expected=None):
        with self.transaction() as tx:
            publication, manifest = self._active(tx, expected)
            builds = [dict(row["build"]) for row in tx.run(
                "MATCH (p:KGPublication {id: $publication})-[h:HAS_BUILD]->(b:KGSourceBuild) "
                "WHERE h.publication_id = $publication RETURN properties(b) AS build ORDER BY b.id LIMIT $limit",
                publication=publication, limit=self.settings.KG_QUERY_MAX_RECORDS + 1)]
            if len(builds) != manifest["counts"]["papers"]:
                raise KGUnavailable("kg_invalid_source_builds")
            allowed = eligible_builds(builds, scope, catalogue)
            records = list(tx.run(
                "MATCH (p:KGPublication {id: $publication})-[i:INCLUDES]->(r:KGRecord) "
                "MATCH (r)-[f:FROM_BUILD]->(b:KGSourceBuild)<-[h:HAS_BUILD]-(p) "
                "WHERE i.publication_id = $publication AND f.publication_id = $publication "
                "AND h.publication_id = $publication AND r.publication_id = $publication "
                "AND b.build_id IN $builds AND r.build_id = b.build_id "
                "RETURN properties(r) AS record, labels(r) AS labels ORDER BY r.id LIMIT $limit",
                publication=publication, builds=list(allowed), limit=self.settings.KG_QUERY_MAX_RECORDS + 1))
            if len(records) > self.settings.KG_QUERY_MAX_RECORDS:
                raise KGUnavailable("kg_query_record_limit")
            parsed = validate_records(records, publication, allowed)
            links = []
            for key, (_, record) in parsed.items():
                if isinstance(record, Observation):
                    links.append(dict(start=identity("record", publication, record.subject_id), end=key, type="HAS_OBSERVATION"))
                elif isinstance(record, Relationship):
                    links.extend(dict(start=key, end=identity("record", publication, target), type=kind)
                                 for kind, target in (("SUBJECT", record.subject_id), ("OBJECT", record.object_id)))
            entity_ids = [key for key, (_, record) in parsed.items() if isinstance(record, Entity)
                          and any(mentioned(name, query) for name in [record.name, *record.aliases])]
            # Read source quotes for ALL scoped records. This both validates provenance
            # and permits exact source-point seeds without relying on flat text indexes.
            sources = list(tx.run(
                "MATCH (r:KGRecord)-[s:SUPPORTED_BY]->(c:KGChunk) "
                "WHERE r.id IN $records AND r.publication_id = $publication AND s.publication_id = $publication "
                "RETURN r.id AS record_id, properties(s) AS support, properties(c) AS chunk "
                "ORDER BY r.id, s.id LIMIT $limit",
                records=list(parsed), publication=publication,
                limit=self.settings.KG_QUERY_MAX_SOURCE_LINKS + 1))
            if len(sources) > self.settings.KG_QUERY_MAX_SOURCE_LINKS:
                raise KGUnavailable("kg_query_source_link_limit")
            by_record, chunks = validate_sources(sources, parsed, allowed)
            if sum(len(c["text"].encode()) for c in chunks.values()) > self.settings.KG_QUERY_MAX_TEXT_BYTES:
                raise KGUnavailable("kg_query_text_limit")
            seed_keys = {(row["collection"], row["id"]) for row in seeds}
            seed_ids = sorted(set(entity_ids) | {key for key, points in by_record.items()
                if any(point in seed_keys for point in points)})
            # Two structural links: entity->assertion->entity, or entity->observation.
            # Every intermediate node/edge must belong to this approved scoped projection.
            traversed = list(tx.run(
                "MATCH path=(seed:KGRecord)-[:HAS_OBSERVATION|SUBJECT|OBJECT*0..2]-(r:KGRecord) "
                "WHERE seed.id IN $seeds AND all(n IN nodes(path) WHERE n.id IN $records "
                "AND n.publication_id = $publication) "
                "AND all(e IN relationships(path) WHERE e.publication_id = $publication "
                "AND any(link IN $links WHERE link.start = startNode(e).id AND link.end = endNode(e).id AND link.type = type(e))) "
                "RETURN r.id AS id, min(length(path)) AS distance ORDER BY distance, id LIMIT $limit",
                seeds=seed_ids, records=list(parsed), links=links, publication=publication,
                limit=self.settings.KG_QUERY_MAX_RECORDS + 1))
            distances = {row["id"]:row["distance"] for row in traversed}
            if set(distances).difference(parsed):
                raise KGUnavailable("kg_traversal_scope_violation")
            tokens = set(normalized(query).split())
            ranked = {}
            for key, distance in distances.items():
                _, record = parsed[key]
                overlap = len(tokens.intersection(normalized(record.model_dump_json()).split()))
                for point in by_record[key]:
                    rank = (distance, -overlap, key)
                    if point not in ranked or rank < ranked[point]:
                        ranked[point] = rank
            ordered = sorted(ranked, key=lambda point: (ranked[point], point))
            result = [to_evidence(chunks[point], allowed[chunks[point]["build_id"]]) for point in ordered[:limit]]
            # A second SQL read excludes changes during graph/vector retrieval. No writer locks.
            if eligible_builds(builds, scope, catalogue) != allowed:
                raise KGUnavailable("kg_source_scope_changed")
            self._active(tx, publication)
            diagnostics = dict(policy=POLICY, publication_id=publication, graph_name=self.settings.KG_GRAPH_NAME,
                extraction_revision=manifest["extraction_revision"], plan_id=manifest["plan_id"],
                graph_paper_count=len(builds), eligible_graph_paper_count=len(allowed),
                graph_build_ids=sorted(allowed), excluded_graph_paper_count=len(builds)-len(allowed),
                matched_entity_ids=sorted(entity_ids), seed_record_count=len(seed_ids),
                validated_record_count=len(parsed),
                traversed_record_ids=sorted(distances), graph_candidate_count=len(ordered),
                graph_candidates_truncated=len(ordered)>limit, graph_chunk_ids=[r.id for r in result],
                scope_kind=scope.kind, traversal_max_links=2, database_writes=0)
            return GraphEvidence(result, diagnostics)


def eligible_builds(builds, boundary, catalogue):
    scopes = boundary.scopes if isinstance(boundary, FederatedRetrievalScope) else (boundary,)
    eligible = {}
    for scope in scopes:
        rows = catalogue.scoped_ready_builds(scope.collection, list(scope.build_ids),
                                              active_only=scope.kind == "active")
        rows = {str(row["id"]): row for row in rows}
        for build in builds:
            row = rows.get(build["build_id"])
            if not row or row.get("deleted") or row.get("status") != "ready":
                continue
            if scope.kind == "active" and str(row.get("active_build")) != build["build_id"]:
                continue
            try:
                validate_target(scope, build["build_id"], build["paper_id"])
            except ValueError:
                continue
            if (str(row["paper_id"]) != build["paper_id"] or row["collection"] != scope.collection
                    or build["collection"] != scope.collection or row["source"] != build["source"]
                    or row["version"] != build["version"]
                    or ((row.get("manifest") or {}).get("artifact") or {}).get("sha256") != build["manifest_sha256"]):
                continue
            eligible[build["build_id"]] = build | dict(metadata=row.get("metadata") or {}, source_id=row.get("source_id"))
    return eligible


def validate_records(rows, publication, builds):
    parsed = {}
    models = {"entity": Entity, "observation": Observation, "relationship": Relationship}
    for row in rows:
        props = dict(row["record"])
        record_type = props["record_type"]
        model = models.get(record_type)
        label = {"entity":"KGEntity", "observation":"KGObservation", "relationship":"KGRelationship"}.get(record_type)
        if model is None or props["publication_id"] != publication or set(row["labels"]) != {"KGRecord", label}:
            raise KGUnavailable("kg_invalid_record")
        record = model.model_validate_json(props["record_json"])
        reviewed = json.loads(props["review_json"])
        build = builds.get(props["build_id"])
        if (not build or props["paper_id"] != build["paper_id"] or props["collection"] != build["collection"]
                or reviewed.get("decision") != "approved" or not reviewed.get("reviewer")
                or props["id"] != identity("record", publication, record.id)
                or props["record_id"] != record.id or props["id"] in parsed
                or isinstance(record, Observation) and record.quarantined):
            raise KGUnavailable("kg_invalid_record")
        parsed[props["id"]] = props, record
    # An observation/relationship cannot become eligible by losing its dependencies.
    for props, record in parsed.values():
        for target in (getattr(record, "subject_id", None), getattr(record, "object_id", None)):
            if target and identity("record", publication, target) not in parsed:
                raise KGUnavailable("kg_missing_record_dependency")
    from .scientific_schema import role_issues
    values = [record for _, record in parsed.values()]
    if role_issues([r for r in values if isinstance(r, Entity)],
                   [r for r in values if isinstance(r, Observation)],
                   [r for r in values if isinstance(r, Relationship)]):
        raise KGUnavailable("kg_invalid_relationship_role")
    return parsed


def validate_sources(rows, parsed, builds):
    by_record = {key:[] for key in parsed}
    seen, chunks = {key:[] for key in parsed}, {}
    for row in rows:
        key, support, chunk = row["record_id"], dict(row["support"]), dict(row["chunk"])
        if key not in parsed:
            raise KGUnavailable("kg_source_scope_violation")
        props, record = parsed[key]
        source = SourceChunk.model_validate({k:chunk[k] for k in SourceChunk.model_fields if k in chunk})
        evidence = json.loads(support["evidence_json"])
        if (chunk["id"] != identity("chunk", source.collection, str(source.point_id))
                or type(chunk.get("chunk_index")) is not int or chunk["chunk_index"] < 0
                or chunk["text_sha256"] != sha256(chunk["text"].encode()).hexdigest()
                or support["publication_id"] != props["publication_id"]
                or support["quote"] != evidence.get("quote") or evidence not in [e.model_dump(mode="json") for e in record.evidence]
                or any(evidence.get(k) != v for k,v in source.model_dump(mode="json").items() if k != "text")
                or evidence["quote"] not in source.text or chunk["build_id"] != props["build_id"]
                or chunk["paper_id"] != props["paper_id"] or chunk["source"] != builds[props["build_id"]]["source"]):
            raise KGUnavailable("kg_invalid_source_provenance")
        point = (source.collection, str(source.point_id))
        if point in chunks and chunks[point] != chunk:
            raise KGUnavailable("kg_conflicting_source_text")
        chunks[point] = chunk
        by_record[key].append(point)
        seen[key].append(evidence)
    for key, (_, record) in parsed.items():
        if sorted(map(canonical, seen[key])) != sorted(canonical(e.model_dump(mode="json")) for e in record.evidence):
            raise KGUnavailable("kg_incomplete_record_provenance")
    return by_record, chunks


def to_evidence(chunk, build):
    metadata = build["metadata"]
    source_id = str(build.get("source_id") or "") if build["source"] == "arxiv" else ""
    authors = metadata.get("authors") or []
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(",") if a.strip()]
    try:
        year = int(str(metadata.get("year") or metadata.get("published"))[:4])
    except (TypeError, ValueError):
        year = None
    return EvidenceChunk(id=chunk["point_id"], text=chunk["text"], collection=chunk["collection"],
        build_id=chunk["build_id"], paper_id=chunk["paper_id"], title=build["title"],
        paper_version=build["version"], arxiv_id=source_id or None,
        source_url=f"https://arxiv.org/abs/{source_id}v{build['version']}" if source_id else None,
        authors=authors, year=year, page=chunk["page_number"],
        section_header=chunk.get("section_header"), chunk_index=chunk["chunk_index"], content_kind="text")


def open_publication(expected=None):
    """Pin before paid work. Reads no application globals and writes nothing."""
    from .settings import KGSettings
    reader = KGReader.connect(KGSettings())
    try:
        return reader.publication(expected)
    except KGUnavailable:
        raise
    except Exception as error:
        raise KGUnavailable("kg_database_unavailable_or_invalid") from error
    finally:
        reader.close()
