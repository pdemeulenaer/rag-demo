"""Read-only index reconciliation, shared by activation and operator audits."""
from uuid import NAMESPACE_URL, uuid5
import math

from qdrant_client import models as m


def expected_ids(build):
    manifest = build.get("manifest") or {}
    if "point_ids" in manifest:
        return [str(value) for value in manifest["point_ids"]]
    # Backward compatibility for existing arXiv v1 manifests, without rewriting them.
    if build.get("source", "arxiv") == "arxiv" and manifest.get("chunk_count"):
        return [str(uuid5(NAMESPACE_URL, f"{build['id']}:{i}")) for i in range(manifest["chunk_count"])]
    return []


def build_filter(build):
    legacy = (build.get("manifest") or {}).get("legacy_filter")
    return m.Filter.model_validate(legacy) if legacy else m.Filter(must=[
        m.FieldCondition(key="build_id", match=m.MatchValue(value=build["id"]))])


def active_filter(active):
    if not active:
        # Match nothing, never fall back to an unfiltered collection.
        return m.Filter(must=[m.HasIdCondition(has_id=[])])
    return m.Filter(should=[
        m.HasIdCondition(has_id=[int(pid) if pid.isdecimal() else pid for pid in expected_ids(b)]) if (b.get("manifest") or {}).get("legacy_filter")
        else build_filter(b) for b in active
    ])


def scan(client, collection, scope=None, vectors=False):
    offset = None
    while True:
        points, offset = client.scroll(collection_name=collection, scroll_filter=scope, offset=offset,
            limit=128, with_vectors=vectors,
            with_payload=["build_id", "paper_id", "paper_version", "file_hash", "file_name", "file_title", "title", "authors", "year", "text"])
        yield from points
        if offset is None:
            break


def valid_vector(vector):
    return isinstance(vector, list) and bool(vector) and any(vector) and all(isinstance(v, (float, int)) and math.isfinite(v) for v in vector)


def check_build(client, build):
    ids = expected_ids(build)
    expected = set(ids)
    if not expected or len(ids) != len(expected) or len(expected) != (build.get("manifest") or {}).get("chunk_count"):
        return {"ok": False, "reason": "missing_expected_point_manifest", "build_id": build["id"]}
    points = list(scan(client, build["collection"], build_filter(build), vectors=True)) if client.collection_exists(build["collection"]) else []
    actual = {str(p.id) for p in points}
    legacy = (build.get("manifest") or {}).get("legacy_filter")
    invalid = [str(p.id) for p in points if not valid_vector(p.vector) or (
        not legacy and ((p.payload or {}).get("paper_id") != build["paper_id"] or
                        (p.payload or {}).get("paper_version") != build["version"]))]
    return {"build_id": build["id"], "ok": expected == actual and not invalid,
            "expected_points": len(expected), "actual_points": len(actual),
            "missing_ids": sorted(expected - actual), "unexpected_ids": sorted(actual - expected),
            "invalid_vector_or_identity_ids": invalid}


def activate_verified(catalogue, client, build, manifest):
    candidate = {**build, "manifest": manifest}
    result = check_build(client, candidate)
    if not result["ok"]:
        raise ValueError("Index verification failed; run papers-audit for details")
    catalogue.activate(build, manifest)


def audit(catalogue, client, collections):
    """No writes, repairs, model calls, status changes or deletions."""
    before = catalogue.all_builds()
    in_progress_ids = {b["id"] for b in before if b["status"] != "ready"}
    checks, retained, incomplete = [], [], []
    claimed = {collection: set() for collection in collections}
    for build in before:
        collection = build["collection"]
        claimed.setdefault(collection, set()).update(expected_ids(build))
        if build["id"] == build["active_build"] and not build["deleted"]:
            checks.append({"source": build["source"], "title": build["metadata"].get("title"),
                           "collection": collection, **check_build(client, build)})
        elif build["status"] == "ready":
            retained.append(build["id"])
        else:
            incomplete.append({"build_id": build["id"], "status": build["status"]})
    unregistered = []
    for collection, known in claimed.items():
        if not client.collection_exists(collection):
            continue
        for point in scan(client, collection):
            if str(point.id) not in known:
                if (point.payload or {}).get("build_id") in in_progress_ids:
                    continue  # A known unfinished job is not an unregistered document.
                unregistered.append({"collection": collection, "point_id": str(point.id),
                    "build_id": (point.payload or {}).get("build_id"),
                    "file_name": (point.payload or {}).get("file_name")})
    # A concurrent activation/update makes this an inconclusive snapshot, not a repair instruction.
    signature = lambda rows: sorted((b["id"], b["updated_at"], b["active_build"], b["deleted"]) for b in rows)
    changed = signature(before) != signature(catalogue.all_builds())
    return {"ok": not changed and all(c["ok"] for c in checks) and not unregistered,
            "concurrent_catalogue_change": changed, "active_builds": checks,
            "unregistered_points": unregistered, "retained_builds": retained, "incomplete_builds": incomplete}


def import_uploads(catalogue, client, collection, embedding_model):
    """Adopt existing vectors into SQL, without changing any Qdrant points.

    The observed point set becomes a baseline; it cannot prove historical extraction
    completeness or infer the original embedding model. Operator supplies that model.
    """
    if not client.collection_exists(collection):
        return {"imported": 0, "already_registered_points": 0}
    groups = {}
    known = {pid for b in catalogue.all_builds() if b["collection"] == collection for pid in expected_ids(b)}
    for point in scan(client, collection, vectors=True):
        payload = point.payload or {}
        if str(point.id) in known or payload.get("build_id"):
            continue
        if not valid_vector(point.vector):
            raise ValueError("Legacy upload has an invalid/missing vector; no automatic repair")
        field = next((key for key in ("file_hash", "file_name", "file_title", "title") if payload.get(key)), None)
        if field is None:
            raise ValueError("Legacy points lack document identity; manual review required")
        groups.setdefault((field, payload[field]), []).append(point)
    imported = 0
    for (field, value), points in groups.items():
        p = points[0].payload
        key = value if field == "file_hash" else f"legacy:{collection}:{field}:{value}"
        meta = {"title": p.get("file_title") or p.get("title") or p.get("file_name"),
                "file_name": p.get("file_name"), "file_hash": p.get("file_hash"),
                "authors": p.get("authors") or [], "year": p.get("year"), "version": 1}
        build = catalogue.upload(key, meta, collection, embedding_model, "legacy-adoption-v1")
        if build["status"] == "ready":
            continue
        ids = [str(point.id) for point in points]
        manifest = {"chunk_count": len(ids), "point_ids": ids, "provenance": "observed_legacy_baseline",
            "embedding_model_assumption": embedding_model,
            "legacy_filter": m.Filter(must=[m.FieldCondition(key=field, match=m.MatchValue(value=value))]).model_dump(mode="json")}
        catalogue.update_build(build["id"], manifest=manifest)
        activate_verified(catalogue, client, build, manifest)
        imported += 1
    return {"imported": imported, "already_registered_points": len(known)}
