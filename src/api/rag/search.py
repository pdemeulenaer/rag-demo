"""Retrieval presets share the same collection and ready-build filter."""
from qdrant_client.models import FieldCondition, Filter, FusionQuery, MatchText, Prefetch


def search_points(client, collection, vector, query, limit, mode="hybrid", scope=None):
    if mode == "vanilla":
        return client.query_points(collection_name=collection, query=vector,
            query_filter=scope, limit=limit)
    if mode != "hybrid":
        raise ValueError(f"Unsupported retrieval mode: {mode}")
    lexical = Filter(must=[FieldCondition(key="text", match=MatchText(text=query))]
                     + ([scope] if scope is not None else []))
    return client.query_points(collection_name=collection,
        prefetch=[Prefetch(query=vector, filter=scope, limit=max(20, limit)),
                  Prefetch(query=vector, filter=lexical, limit=max(20, limit))],
        query=FusionQuery(fusion="rrf"), query_filter=scope, limit=limit)
