"""Dense, BM25 and fused retrieval over one explicitly scoped collection."""
from qdrant_client.models import FusionQuery, Prefetch

from src.api.rag.sparse import SPARSE_VECTOR_NAME, query_sparse_vector


def search_points(client, collection, vector, query, limit, mode="hybrid", scope=None):
    if mode in {"vanilla", "dense"}:
        if vector is None:
            raise ValueError("Dense retrieval requires a query embedding")
        return client.query_points(collection_name=collection, query=vector,
            query_filter=scope, limit=limit)
    sparse = query_sparse_vector(query)
    if mode == "sparse":
        return client.query_points(
            collection_name=collection, query=sparse, using=SPARSE_VECTOR_NAME,
            query_filter=scope, limit=limit,
        )
    if mode != "hybrid":
        raise ValueError(f"Unsupported retrieval mode: {mode}")
    if vector is None:
        raise ValueError("Hybrid retrieval requires a query embedding")
    return client.query_points(collection_name=collection,
        prefetch=[
            Prefetch(query=vector, filter=scope, limit=max(20, limit)),
            Prefetch(query=sparse, using=SPARSE_VECTOR_NAME,
                     filter=scope, limit=max(20, limit)),
        ],
        query=FusionQuery(fusion="rrf"), query_filter=scope, limit=limit)
