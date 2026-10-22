"""Dense, BM25 and fused retrieval over one explicitly scoped collection."""
from qdrant_client.models import FusionQuery, Prefetch

from src.api.rag.sparse import SPARSE_VECTOR_NAME, query_sparse_vector
from src.api.observability.stage_timings import measure_stage


def _query_points(client, **kwargs):
    # Only the Qdrant call: excludes embedding, BM25 vector construction and
    # evidence validation. All modes, federated collections and tools share it.
    with measure_stage("qdrant_seconds"):
        return client.query_points(**kwargs)


def search_points(client, collection, vector, query, limit, mode="hybrid", scope=None):
    if mode in {"vanilla", "dense"}:
        if vector is None:
            raise ValueError("Dense retrieval requires a query embedding")
        return _query_points(client, collection_name=collection, query=vector,
            query_filter=scope, limit=limit)
    sparse = query_sparse_vector(query)
    if mode == "sparse":
        return _query_points(client,
            collection_name=collection, query=sparse, using=SPARSE_VECTOR_NAME,
            query_filter=scope, limit=limit,
        )
    if mode != "hybrid":
        raise ValueError(f"Unsupported retrieval mode: {mode}")
    if vector is None:
        raise ValueError("Hybrid retrieval requires a query embedding")
    return _query_points(client, collection_name=collection,
        prefetch=[
            Prefetch(query=vector, filter=scope, limit=max(20, limit)),
            Prefetch(query=sparse, using=SPARSE_VECTOR_NAME,
                     filter=scope, limit=max(20, limit)),
        ],
        query=FusionQuery(fusion="rrf"), query_filter=scope, limit=limit)
