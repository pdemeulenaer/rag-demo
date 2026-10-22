"""Independent CLI configuration; preview/schema never instantiate this class."""
from pydantic import Field, SecretStr

from src.api.papers.settings import PaperSettings


class KGSettings(PaperSettings):
    QDRANT_COLLECTION_NAME: str = "uploaded_papers_v2"
    # Bounded frozen input batches, not whole-corpus in-memory preparation.
    KG_PREPARE_MAX_PAPERS: int = Field(100,ge=1,le=1000)
    KG_PREPARE_MAX_CHUNKS: int = Field(20000,ge=1,le=100000)
    KG_PREPARE_MAX_BYTES: int = Field(50000000,ge=10000,le=500000000)
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: SecretStr = SecretStr("neo4j-local-only")
    NEO4J_DATABASE: str = "neo4j"
    KG_GRAPH_NAME: str = Field("star-clusters-pilot", pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")
    KG_NEO4J_TIMEOUT_SECONDS: int = Field(30, ge=1, le=300)
    KG_PUBLISH_MAX_RECORDS: int = Field(10000, ge=1, le=50000)
    KG_PUBLISH_MAX_BYTES: int = Field(10000000, ge=10000, le=50000000)
    # Read-only pilot traversal bounds. Fail explicitly, never truncate validation.
    KG_QUERY_PUBLICATION_ID: str = ""
    KG_QUERY_MAX_RECORDS: int = Field(2000, ge=1, le=50000)
    KG_QUERY_MAX_CHUNKS: int = Field(20, ge=1, le=50)
    KG_QUERY_HYBRID_CANDIDATES: int = Field(20, ge=1, le=100)
    KG_QUERY_MAX_SOURCE_LINKS: int = Field(20000, ge=1, le=1000000)
    KG_QUERY_MAX_TEXT_BYTES: int = Field(10000000, ge=10000, le=50000000)
    OPENAI_API_KEY: SecretStr = SecretStr("")
    KG_MODEL: str = "gpt-5-mini"
    KG_REASONING_EFFORT: str = "low"
    KG_MAX_COMPLETION_TOKENS: int = Field(16384, ge=1024, le=32768)
    KG_TIMEOUT_SECONDS: int = Field(180, ge=10, le=600)
    KG_MAX_CALLS: int = Field(10, ge=1, le=1000)
    KG_CONCURRENCY: int = Field(2, ge=1, le=8)
    LANGFUSE_ENABLED: bool = False
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: SecretStr = SecretStr("")
    LANGFUSE_BASE_URL: str = "http://localhost:3000"
