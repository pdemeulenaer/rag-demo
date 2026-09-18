"""Select a RAG mode without mixing mode-specific orchestration."""
from src.api.rag.modes import hybrid, hybrid_rerank, vanilla


def retrieve_for_mode(mode, query, client, *, top_k, collection, scope,
                      retrieve_context, rerank_context):
    if mode == "vanilla":
        return vanilla.retrieve(query, client, top_k=top_k, collection=collection,
                                scope=scope, retrieve_context=retrieve_context)
    if mode == "hybrid":
        return hybrid.retrieve(query, client, top_k=top_k, collection=collection,
                               scope=scope, retrieve_context=retrieve_context)
    if mode == "hybrid_rerank":
        return hybrid_rerank.retrieve(
            query, client, top_k=top_k, collection=collection, scope=scope,
            retrieve_context=retrieve_context,
                               rerank_context=rerank_context)
    raise ValueError(f"Unsupported RAG mode: {mode}")
