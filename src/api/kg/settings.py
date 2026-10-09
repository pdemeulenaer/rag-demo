"""Independent CLI configuration; preview/schema never instantiate this class."""
from pydantic import Field, SecretStr

from src.api.papers.settings import PaperSettings


class KGSettings(PaperSettings):
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
