from hashlib import sha256
import json
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PaperSettings(BaseSettings):
    """Independent settings: metadata discovery needs no model API keys."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    PAPERS_DATABASE_URL: str = "postgresql+psycopg://rag:rag@localhost:5432/papers"
    PAPERS_COLLECTION: str = "arxiv_papers_v1"
    PAPERS_ARTIFACT_DIR: Path = Path("data/paper_artifacts")
    PAPERS_STORAGE_MODE: str = "LOCAL"
    PAPERS_AZURE_CONTAINER: str = "rag-papers"
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    ARXIV_CATEGORIES: str = "astro-ph.GA"
    ARXIV_TOPIC_TERMS: str = (
        "star cluster,stellar cluster,globular cluster,open cluster,"
        "young massive cluster,nuclear star cluster"
    )
    ARXIV_USER_AGENT: str = "rag-demo/0.2 (scientific-paper research demo)"
    ARXIV_BACKFILL_DAYS: int = Field(7, ge=1, le=365)
    ARXIV_DAILY_LIMIT: int = Field(10, ge=1, le=100)
    ARXIV_MAX_ATTEMPTS: int = Field(3, ge=1, le=10)
    ARXIV_MAX_PDF_MB: int = Field(30, ge=1, le=200)
    ARXIV_MAX_CHUNKS: int = Field(1000, ge=1, le=10000)
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    @field_validator("ARXIV_CATEGORIES")
    @classmethod
    def validate_categories(cls, value):
        import re
        categories = [c.strip() for c in value.split(",") if c.strip()]
        if not categories or any(not re.fullmatch(r"[a-z-]+(?:\.[A-Z]{2})?", c) for c in categories):
            raise ValueError("Expected comma-separated arXiv category identifiers")
        return ",".join(sorted(set(categories)))

    @field_validator("PAPERS_STORAGE_MODE")
    @classmethod
    def validate_storage(cls, value):
        if value.upper() not in {"LOCAL", "AZURE"}:
            raise ValueError("PAPERS_STORAGE_MODE must be LOCAL or AZURE")
        return value.upper()

    @property
    def categories(self):
        return self.ARXIV_CATEGORIES.split(",")

    @property
    def terms(self):
        return sorted({t.strip().lower() for t in self.ARXIV_TOPIC_TERMS.split(",") if t.strip()})

    @property
    def scope_id(self):
        return sha256(json.dumps([self.categories, self.terms]).encode()).hexdigest()[:16]

    @property
    def pipeline_id(self):
        # Bump extractor version when parsing/chunking/payload semantics change.
        spec = ["pymupdf-text-v1", "chars=1800,overlap=200", self.EMBEDDING_MODEL,
                self.PAPERS_COLLECTION]
        return sha256(json.dumps(spec).encode()).hexdigest()[:16]
