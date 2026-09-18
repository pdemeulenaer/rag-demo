"""Deterministic safety policies around the model-driven LangGraph loop."""
from __future__ import annotations

import json
from hashlib import sha256

from qdrant_client.models import FieldCondition, Filter, MatchAny

from src.api.rag.contracts import RetrievalScope


def action_fingerprint(name: str, arguments: dict) -> str:
    payload = json.dumps({"name": name, "arguments": arguments}, sort_keys=True,
                         separators=(",", ":"), default=str)
    return sha256(payload.encode()).hexdigest()


def narrow_scope(scope: RetrievalScope, build_ids: list[str] | None,
                 paper_ids: list[str] | None) -> RetrievalScope:
    """Intersect model-requested filters with the immutable approved corpus."""
    requested_builds = tuple(dict.fromkeys(build_ids or scope.build_ids))
    if set(requested_builds).difference(scope.build_ids):
        raise ValueError("Agent requested a build outside the approved corpus")

    requested_papers = tuple(dict.fromkeys(paper_ids or ()))
    known_papers = {build.paper_id for build in scope.builds if build.paper_id}
    if requested_papers and known_papers and not set(requested_papers).issubset(known_papers):
        raise ValueError("Agent requested a paper outside the approved corpus")

    selected = tuple(build for build in scope.builds
                     if build.build_id in requested_builds)
    narrowed_filter = Filter(must=[
        scope.qdrant_filter(),
        FieldCondition(key="build_id", match=MatchAny(any=list(requested_builds))),
    ])
    return RetrievalScope(
        collection=scope.collection, build_ids=requested_builds, kind=scope.kind,
        paper_ids=requested_papers, builds=selected, filter_override=narrowed_filter,
    )
