"""Small transactional Neo4j adapter for immutable publication snapshots.

All values are parameters. Labels/types come solely from application allowlists.
No APOC, entity merging, generic Cypher tool or default GraphRAG writer activation.
"""
from collections import defaultdict
from contextlib import contextmanager
import json

from neo4j import GraphDatabase, READ_ACCESS

from .jobs import canonical
from .scientific_schema import ROLE_RULES

LABELS = {"KGPaper", "KGSourceBuild", "KGChunk", "KGEntity", "KGObservation", "KGRelationship"}
RECORD_LABELS = {"KGEntity", "KGObservation", "KGRelationship"}
EDGE_TYPES = {"HAS_BUILD", "OF_PAPER", "HAS_CHUNK", "INCLUDES", "FROM_BUILD", "SUPPORTED_BY",
              "HAS_OBSERVATION", "SUBJECT", "OBJECT", *(key.upper() for key in ROLE_RULES)}


class Neo4jStore:
    def __init__(self, driver, database="neo4j", timeout=30):
        self.driver, self.database, self.timeout = driver, database, timeout

    @classmethod
    def connect(cls, settings):
        driver = GraphDatabase.driver(settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD.get_secret_value()),
            connection_timeout=settings.KG_NEO4J_TIMEOUT_SECONDS, max_transaction_retry_time=0)
        return cls(driver, settings.NEO4J_DATABASE, settings.KG_NEO4J_TIMEOUT_SECONDS)

    def close(self):
        self.driver.close()

    @contextmanager
    def transaction(self, *, read=False):
        options = dict(database=self.database)
        if read:
            options["default_access_mode"] = READ_ACCESS
        with self.driver.session(**options) as session:
            with session.begin_transaction(timeout=self.timeout) as tx:
                yield tx
                tx.commit()  # Exceptions exit without commit; the driver rolls back.

    def constraints(self):
        # DDL has its own transaction; a failed data stage may leave harmless constraints.
        with self.transaction() as tx:
            for label, field in [("KGPublication", "id"), ("KGCorpus", "name"),
                                 ("KGRecord", "id"), ("KGPaper", "id"),
                                 ("KGSourceBuild", "id"), ("KGChunk", "id")]:
                tx.run(f"CREATE CONSTRAINT kg_{label.lower()}_{field} IF NOT EXISTS "
                       f"FOR (n:{label}) REQUIRE n.{field} IS UNIQUE").consume()

    @staticmethod
    def _lock(tx, name):
        # One write lock serializes stage/activate for this named graph. No destructive cleanup.
        row = tx.run("MERGE (c:KGCorpus {name: $name}) "
            "ON CREATE SET c.active_publication_id = '' SET c.name = $name "
            "RETURN c.active_publication_id AS active", name=name).single()
        if row is None or not isinstance(row["active"], str):
            raise ValueError("Graph activation pointer is invalid")
        return row["active"]

    @staticmethod
    def _publication(tx, publication_id):
        row = tx.run("MATCH (p:KGPublication {id: $id}) RETURN properties(p) AS properties",
                     id=publication_id).single()
        return dict(row["properties"]) if row else None

    @staticmethod
    def _audit(tx, payload):
        publication = Neo4jStore._publication(tx, payload["id"])
        expected = dict(id=payload["id"], graph_name=payload["graph_name"], manifest_json=canonical(payload["manifest"]))
        if (publication is None or publication.get("status") not in {"staged", "active", "retired"}
                or {k:v for k,v in publication.items() if k != "status"} != expected):
            raise ValueError("Staged publication metadata differs; stage the exact reviewed content first")
        corpus = tx.run("MATCH (c:KGCorpus {name: $name}) RETURN c.active_publication_id AS active",
                        name=payload["graph_name"]).single()
        if corpus is None or (publication["status"] == "active") != (corpus["active"] == payload["id"]):
            raise ValueError("Publication status differs from its activation pointer")
        ids = [node["id"] for node in payload["nodes"]]
        rows = list(tx.run("MATCH (n) WHERE n.id IN $ids OR (n:KGRecord AND n.publication_id = $publication) "
            "RETURN n.id AS id, labels(n) AS labels, properties(n) AS properties",
            ids=ids, publication=payload["id"]))
        actual = {}
        for row in rows:
            if row["id"] in actual:
                raise ValueError("Duplicate publication node identity")
            actual[row["id"]] = row
        if set(actual) != set(ids):
            raise ValueError("Publication node set differs from approved projection")
        for node in payload["nodes"]:
            labels = {node["label"]} | ({"KGRecord"} if node["label"] in RECORD_LABELS else set())
            row = actual[node["id"]]
            if set(row["labels"]) != labels or dict(row["properties"]) != node["properties"]:
                raise ValueError("Publication node content differs from approved projection")
        rows = list(tx.run("MATCH (s)-[r]->(o) WHERE r.publication_id = $publication "
            "OR s.publication_id = $publication OR o.publication_id = $publication "
            "OR (s:KGPublication AND s.id = $publication) OR (o:KGPublication AND o.id = $publication) "
            "RETURN type(r) AS type, s.id AS start, o.id AS end, properties(r) AS properties",
            publication=payload["id"]))
        actual_edges = [dict(type=r["type"], start=r["start"], end=r["end"], properties=dict(r["properties"])) for r in rows]
        if sorted(canonical(r) for r in actual_edges) != sorted(canonical(r) for r in payload["edges"]):
            raise ValueError("Publication edge/provenance set differs from approved projection")
        return publication["status"]

    def stage(self, payload, recheck):
        self.constraints()
        with self.transaction() as tx:
            active = self._lock(tx, payload["graph_name"])
            if self._publication(tx, payload["id"]) is None:
                tx.run("CREATE (p:KGPublication {id: $id, graph_name: $name, manifest_json: $manifest, status: 'staged'})",
                    id=payload["id"], name=payload["graph_name"], manifest=canonical(payload["manifest"])).consume()
                grouped = defaultdict(list)
                for node in payload["nodes"]:
                    if node["label"] not in LABELS:
                        raise ValueError("Unexpected publication label")
                    grouped[node["label"]].append(node)
                for label, nodes in grouped.items():
                    labels = "KGRecord:" + label if label in RECORD_LABELS else label
                    rows = list(tx.run(f"UNWIND $rows AS row MERGE (n:{labels} {{id: row.id}}) "
                        "ON CREATE SET n = row.properties RETURN n.id AS id, properties(n) AS properties", rows=nodes))
                    if len(rows) != len(nodes) or {r["id"]:dict(r["properties"]) for r in rows} != {r["id"]:r["properties"] for r in nodes}:
                        raise ValueError("Immutable source/record identity conflict")
                grouped = defaultdict(list)
                for edge in payload["edges"]:
                    if edge["type"] not in EDGE_TYPES:
                        raise ValueError("Unexpected scientific relationship type")
                    grouped[edge["type"]].append(edge)
                for kind, edges in grouped.items():
                    result = tx.run("UNWIND $rows AS row MATCH (s {id: row.start}), (o {id: row.end}) "
                        f"MERGE (s)-[r:{kind} {{id: row.properties.id}}]->(o) "
                        "ON CREATE SET r = row.properties RETURN count(r) AS count", rows=edges).single()
                    if result is None or result["count"] != len(edges):
                        raise ValueError("Publication relationship endpoints are missing or duplicated")
            status = self._audit(tx, payload)  # Also rejects drift instead of repairing existing graphs.
            recheck()
            return dict(status=status, active_publication_id=active or None, activated=active == payload["id"])

    def verify(self, payload, recheck):
        with self.transaction(read=True) as tx:
            status = self._audit(tx, payload)
            recheck()
            return dict(status=status, verified=True, database_writes=0)

    def activate(self, payload, expect_active, recheck):
        with self.transaction() as tx:
            active = self._lock(tx, payload["graph_name"])
            status = self._audit(tx, payload)
            if active == payload["id"]:
                if status != "active":
                    raise ValueError("Active graph pointer/status conflict")
            else:
                if active != (expect_active or ""):
                    raise ValueError("Active publication changed; inspect status and explicitly set KG_EXPECT_ACTIVE")
                if status not in {"staged", "retired"}:
                    raise ValueError("Publication is not eligible for activation")
                if active:
                    old = self._publication(tx, active)
                    if old is None or old.get("graph_name") != payload["graph_name"] or old.get("status") != "active":
                        raise ValueError("Previous activation pointer/status conflict")
                    tx.run("MATCH (p:KGPublication {id: $id}) SET p.status = 'retired'", id=active).consume()
                tx.run("MATCH (c:KGCorpus {name: $name}), (p:KGPublication {id: $id}) "
                    "SET c.active_publication_id = p.id, p.status = 'active'", name=payload["graph_name"], id=payload["id"]).consume()
            recheck()  # Before commit; a changed/deleted SQL source aborts the pointer switch too.
            return dict(status="active", activated=True, previous_publication_id=active or None,
                        active_publication_id=payload["id"])

    def status(self, graph_name):
        with self.transaction(read=True) as tx:
            row = tx.run("MATCH (c:KGCorpus {name: $name}) RETURN c.active_publication_id AS active", name=graph_name).single()
            publications = list(tx.run("MATCH (p:KGPublication {graph_name: $name}) "
                "RETURN p.id AS id, p.status AS status, p.manifest_json AS manifest ORDER BY p.id LIMIT 51", name=graph_name))
            return dict(graph_name=graph_name, active_publication_id=row["active"] if row and row["active"] else None,
                publications=[dict(publication_id=p["id"], status=p["status"], counts=json.loads(p["manifest"])["counts"]) for p in publications[:50]],
                history_limit=50, history_truncated=len(publications)>50,
                catalogue_checked=False, content_verified=False, graph_ready=False,
                query_readiness="not_checked", database_writes=0, model_calls=0)
