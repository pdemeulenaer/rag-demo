"""Deterministic BM25 sparse vectors shared by ingestion and retrieval.

Qdrant supplies the corpus-dependent IDF component.  This module supplies a
stable token mapping plus the BM25 term-frequency/document-length component,
so it works identically with local Qdrant and Qdrant Cloud without inference
services or an additional model download.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import re
import unicodedata

from qdrant_client import models as m


SPARSE_VECTOR_NAME = "bm25"
BM25_SPEC = "bm25-sha256-word-v1"
BM25_K = 1.2
BM25_B = 0.75
BM25_AVERAGE_CHUNK_TOKENS = 256.0
TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:[-_.][a-z0-9]+)*")


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return TOKEN_PATTERN.findall(normalized.casefold())


def _token_id(token: str) -> int:
    # Qdrant sparse indices are unsigned integers.  A stable 31-bit digest is
    # reproducible across Python processes, unlike the built-in hash().
    return int.from_bytes(sha256(token.encode()).digest()[:4], "big") & 0x7FFFFFFF


def document_sparse_vector(text: str) -> m.SparseVector:
    """Encode the BM25 TF/length component for one indexed chunk."""
    tokens = _tokens(text)
    counts = Counter(tokens)
    length = len(tokens)
    values = {}
    for token, frequency in counts.items():
        denominator = frequency + BM25_K * (
            1 - BM25_B + BM25_B * length / BM25_AVERAGE_CHUNK_TOKENS
        )
        values[_token_id(token)] = frequency * (BM25_K + 1) / denominator
    ordered = sorted(values.items())
    return m.SparseVector(
        indices=[index for index, _ in ordered],
        values=[value for _, value in ordered],
    )


def query_sparse_vector(text: str) -> m.SparseVector:
    """Encode unique query terms; Qdrant applies live collection IDF values."""
    indices = sorted({_token_id(token) for token in _tokens(text)})
    if not indices:
        raise ValueError("BM25 query contains no searchable terms")
    return m.SparseVector(indices=indices, values=[1.0] * len(indices))


def point_vectors(dense: list[float], text: str) -> dict:
    return {"": dense, SPARSE_VECTOR_NAME: document_sparse_vector(text)}


def retrieval_index_manifest() -> dict:
    return {
        "dense_vector_name": "",
        "sparse_vector_name": SPARSE_VECTOR_NAME,
        "sparse_model": BM25_SPEC,
        "fusion": "rrf",
    }


def ensure_hybrid_collection(client, collection: str, dimension: int) -> None:
    """Create or validate the immutable dense+BM25 collection contract."""
    if not client.collection_exists(collection):
        client.create_collection(
            collection_name=collection,
            vectors_config=m.VectorParams(size=dimension, distance=m.Distance.COSINE),
            sparse_vectors_config={
                SPARSE_VECTOR_NAME: m.SparseVectorParams(modifier=m.Modifier.IDF)
            },
        )
        return
    info = client.get_collection(collection)
    if getattr(info.config.params.vectors, "size", None) != dimension:
        raise ValueError("Embedding dimension mismatch; use a new Qdrant collection")
    sparse = getattr(info.config.params, "sparse_vectors", None) or {}
    params = sparse.get(SPARSE_VECTOR_NAME)
    if params is None or getattr(params, "modifier", None) != m.Modifier.IDF:
        raise ValueError(
            "Collection lacks the required BM25/IDF sparse vector; configure a new "
            "collection name and re-index"
        )
