from contextlib import closing

import pytest
from qdrant_client import QdrantClient, models as m

from src.api.rag.search import search_points
from src.api.rag.sparse import ensure_hybrid_collection, point_vectors


def test_bm25_recovers_identifier_that_dense_ranks_second():
    with closing(QdrantClient(":memory:")) as client:
        ensure_hybrid_collection(client, "papers", 2)
        client.upsert("papers", [
            m.PointStruct(
                id=1, vector=point_vectors([1.0, 0.0], "Milky Way cluster mass function"),
                payload={"text": "Milky Way cluster mass function"},
            ),
            m.PointStruct(
                id=2, vector=point_vectors([0.9, 0.1], "M33 star cluster catalogue"),
                payload={"text": "M33 star cluster catalogue"},
            ),
        ])

        dense = search_points(client, "papers", [1.0, 0.0], "M33", 2, "vanilla")
        sparse = search_points(client, "papers", None, "M33", 2, "sparse")
        hybrid = search_points(client, "papers", [1.0, 0.0], "M33", 2, "hybrid")

        assert dense.points[0].id == 1
        assert [point.id for point in sparse.points] == [2]
        assert hybrid.points[0].id == 2


def test_dense_only_collection_is_rejected_for_new_ingestion():
    with closing(QdrantClient(":memory:")) as client:
        client.create_collection(
            "old", vectors_config=m.VectorParams(size=2, distance=m.Distance.COSINE)
        )
        with pytest.raises(ValueError, match="new collection name"):
            ensure_hybrid_collection(client, "old", 2)
