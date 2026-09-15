"""Provider clients shared by the online RAG path.

The Langfuse OpenAI class is a drop-in SDK wrapper. It automatically records
model, latency, token usage and errors inside the current application span.
"""
from functools import lru_cache

from src.api.core.config import config


def openai_class():
    if config.LANGFUSE_ENABLED:
        # Importing the shim first bridges pydantic settings into the environment
        # before Langfuse initializes its global OpenTelemetry client.
        import src.api.observability.tracing  # noqa: F401
        from langfuse.openai import OpenAI
    else:
        from openai import OpenAI
    return OpenAI


@lru_cache(maxsize=1)
def openai_client():
    return openai_class()(api_key=config.OPENAI_API_KEY)
