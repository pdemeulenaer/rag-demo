"""Vanilla RAG: one dense-vector retrieval pass."""


def retrieve(query, client, *, top_k, collection, scope, retrieve_context):
    return retrieve_context(query, client, top_k=top_k, mode="vanilla",
                            collection=collection, scope=scope)
