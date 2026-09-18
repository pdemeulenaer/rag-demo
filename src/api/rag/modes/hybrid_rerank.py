"""Hybrid-Rerank RAG: dense+BM25 RRF candidates followed by Cohere."""


def retrieve(query, client, *, top_k, collection, scope,
             retrieve_context, rerank_context):
    candidates = retrieve_context(
        query, client, top_k=max(20, top_k), mode="hybrid",
        collection=collection, scope=scope,
    )
    return rerank_context(query, candidates, top_n=top_k)
