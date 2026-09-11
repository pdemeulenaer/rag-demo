"""Select existing active arXiv papers for a versioned extraction upgrade."""
from uuid import NAMESPACE_URL, uuid5

from .arxiv import Paper


def preview(catalogue, settings):
    """Read only; no discovery, PDF requests, or embedding calls."""
    targets = []
    for old in catalogue.active(settings):
        if old["pipeline_id"] == settings.pipeline_id:
            continue
        target_id = str(uuid5(NAMESPACE_URL, f"{old['version_id']}:{settings.pipeline_id}"))
        existing = catalogue.get_build(target_id)
        status = existing["status"] if existing else "not_queued"
        blocked = bool(existing and (existing["attempts"] >= settings.ARXIV_MAX_ATTEMPTS or status == "ready"))
        targets.append({"paper_id": old["paper_id"], "title": old["metadata"]["title"],
                        "version": old["version"], "old_build_id": old["id"],
                        "target_build_id": target_id, "status": status, "blocked": blocked})
    return targets


def select_replacements(catalogue, settings, limit):
    """Caller holds writer lock. Queue only selected replacements, not backlog."""
    candidates = preview(catalogue, settings)
    selected = []
    for row in candidates:
        if row["blocked"]:
            continue
        old = catalogue.get_build(row["old_build_id"])
        target_id = catalogue.discover(Paper(**old["metadata"]), settings)
        if target_id != row["target_build_id"]:
            raise ValueError("Replacement build identity mismatch")
        selected.append(catalogue.get_build(target_id))
        if len(selected) >= limit:
            break
    return selected
