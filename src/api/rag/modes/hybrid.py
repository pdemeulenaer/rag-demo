"""Hybrid RAG: dense/text RRF retrieval followed by Cohere reranking."""


def retrieve(query, client, *, top_k, collection, scope, retrieve_context, rerank_context):
    candidates = retrieve_context(query, client, top_k=20, mode="hybrid",
                                  collection=collection, scope=scope)
    return rerank_context(query, candidates, top_n=top_k)
