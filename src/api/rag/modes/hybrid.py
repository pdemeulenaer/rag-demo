"""Hybrid RAG: dense and BM25 candidates fused with reciprocal-rank fusion."""


def retrieve(query, client, *, top_k, collection, scope, retrieve_context):
    return retrieve_context(query, client, top_k=top_k, mode="hybrid",
                            collection=collection, scope=scope)
