"""Hybrid RAG: dense and BM25 candidates fused with reciprocal-rank fusion."""
from .named_selection import select_named_context


def retrieve(query, client, *, top_k, collection, scope, retrieve_context, required_papers=()):
    # One embedding/search, no per-paper retry. Ordinary questions are unchanged.
    limit = max(20, top_k) if required_papers else top_k
    candidates = retrieve_context(query, client, top_k=limit, mode="hybrid",
                                 collection=collection, scope=scope)
    if not required_papers:
        return candidates
    result = select_named_context(candidates, required_papers, top_k)
    result.diagnostics["hybrid_candidate_limit"] = limit
    return result
