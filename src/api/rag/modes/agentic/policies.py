"""Deterministic safety policies around the model-driven LangGraph loop."""
from __future__ import annotations

import json
import re
from hashlib import sha256

from qdrant_client.models import FieldCondition, Filter, MatchAny

from src.api.rag.contracts import EvidenceChunk, RetrievalScope


_ROUTING_HINT = re.compile(
    r"\s*\(\s*(?:paper_id|required_build_id)\s*=\s*[A-Za-z0-9-]{1,128}"
    r"(?:\s*;\s*(?:paper_id|required_build_id)\s*=\s*[A-Za-z0-9-]{1,128})*\s*\)"
)
_BUILD_ID_FIELD = re.compile(r"(?:\(|;)\s*required_build_id\s*=\s*([A-Za-z0-9-]{1,128})")
_LONG_TITLE = re.compile(r"['\"“]([^'\"“”]{25,})['\"”]")


def focused_requirement_text(description: str) -> str:
    """Remove routing metadata and a resolved paper title from a fact query."""
    without_hint = _ROUTING_HINT.sub(" ", description)
    without_title = _LONG_TITLE.sub(" ", without_hint)
    return " ".join(without_title.split()).strip() or " ".join(without_hint.split()).strip()


def scoped_requirement_query(description: str, required_build_ids: list[str],
                             required_titles: dict[str, str] | None = None, *,
                             explicit_build_ids: bool = False,
                             required_source_ids: dict[str, str] | None = None) -> tuple[str, list[str]]:
    """Use a resolved build as a filter, never as dense/sparse search text."""
    allowed = set(required_build_ids)
    builds = list(dict.fromkeys(
        match.group(1)
        for hint in _ROUTING_HINT.finditer(description)
        for match in _BUILD_ID_FIELD.finditer(hint.group())
        if match.group(1) in allowed
    ))
    if explicit_build_ids:
        builds = list(dict.fromkeys(required_build_ids))
    query = _ROUTING_HINT.sub(" ", description)
    # Infer a filter only from a catalogue-confirmed full title/reference, never
    # a topic word, partial title or arbitrary paper identity suggested by the model.
    candidate_builds = builds or list(required_titles or {})
    inferred = []
    for build_id in candidate_builds:
        title = (required_titles or {}).get(build_id, "")
        words = re.findall(r"\w+", title)
        title_pattern = (r"(?<!\w)" + r"[\W_]+".join(map(re.escape, words)) + r"(?!\w)"
                         if words else None)
        source_id = (required_source_ids or {}).get(build_id)
        source_pattern = (r"(?<![\w.])" + re.escape(source_id) + r"(?:v[1-9]\d*)?(?!\w)"
                          if source_id else None)
        if ((title_pattern and re.search(title_pattern, query, re.I))
                or (source_pattern and re.search(source_pattern, query, re.I))):
            inferred.append(build_id)
    if not builds:
        builds = inferred
    for build_id in builds:
        # Confirmed build IDs belong in filters, even if emitted as bare UUIDs.
        query = re.sub(r"(?<!\w)" + re.escape(build_id) + r"(?!\w)", " ", query, flags=re.I)
        # Models also copy short UUID labels into content queries. Strip only an
        # actual prefix (>=8 chars) of this already-filtered, confirmed UUID.
        # A prefix never infers a filter, and unknown identifiers remain untouched.
        if re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", build_id, re.I):
            query = re.sub(
                r"(?<!\w)[0-9a-f-]{8,36}(?!\w)",
                lambda match: " " if build_id.lower().startswith(match.group().lower())
                else match.group(), query, flags=re.I,
            )
        title = (required_titles or {}).get(build_id)
        if title:
            # Remove only catalogue-confirmed titles; a science phrase that merely
            # resembles a title may still be essential to the factual query.
            words = re.findall(r"\w+", title)
            query = re.sub(
                r"(?:\b(?:as reported in|in|from)\s+)?[\"“”']?(?<!\w)"
                + r"[\W_]+".join(map(re.escape, words)) + r"(?!\w)[\"“”']?",
                " ", query, flags=re.IGNORECASE,
            )
        source_id = (required_source_ids or {}).get(build_id)
        if source_id:
            query = re.sub(
                r"(?:(?:https?://)?(?:export\.)?arxiv\.org/(?:abs|pdf)/"
                r"|\(?\s*arxiv\s*:?\s*)?(?<![\w.])" + re.escape(source_id)
                + r"(?:v[1-9]\d*)?(?!\w)(?:\.pdf)?\)?", " ", query, flags=re.I,
            )
    if builds and not required_titles:
        query = _LONG_TITLE.sub(" ", query)
    query = re.sub(r"\s+([.,;:])", r"\1", query)
    query = query.strip(" ,:;")
    return (" ".join(query.split())[:500] or ("paper findings" if builds else description[:500]), builds)


def action_fingerprint(name: str, arguments: dict) -> str:
    # need_id is observability metadata, not retrieval behavior. Excluding it
    # prevents a planner from evading duplicate-call protection by renaming a need.
    effective_arguments = {key: value for key, value in arguments.items()
                           if key != "need_id"}
    payload = json.dumps({"name": name, "arguments": effective_arguments}, sort_keys=True,
                         separators=(",", ":"), default=str)
    return sha256(payload.encode()).hexdigest()


def observed_section_header(header: str, evidence: list[EvidenceChunk], *,
                            build_id: str | None, paper_id: str | None) -> str:
    """Recover presentation-only heading changes from this exact observed paper."""
    def normalize(text):
        value = re.sub(r"^\s*#{1,6}\s+", "", str(text)).strip()
        if value.startswith("**") and value.endswith("**"):
            value = value[2:-2]
        return " ".join(value.split())

    observed = {row.section_header for row in evidence
                if row.build_id == build_id and row.paper_id == paper_id and row.section_header
                and normalize(row.section_header) == normalize(header)}
    return observed.pop() if len(observed) == 1 else header


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
