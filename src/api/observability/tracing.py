"""Small Langfuse v4 shim used by runtime RAG and offline evaluations.

Application modules import from here rather than from Langfuse directly.  With
``LANGFUSE_ENABLED=false`` all helpers are no-ops and Langfuse is not imported.
This keeps tracing unable to become a runtime dependency when it is disabled.
"""
from contextlib import contextmanager
from functools import wraps
import os

from src.api.core.config import config


def _bridge_environment() -> None:
    values = {
        "LANGFUSE_PUBLIC_KEY": config.LANGFUSE_PUBLIC_KEY,
        "LANGFUSE_SECRET_KEY": config.LANGFUSE_SECRET_KEY,
        "LANGFUSE_BASE_URL": config.LANGFUSE_BASE_URL,
        "LANGFUSE_ENVIRONMENT": config.LANGFUSE_ENVIRONMENT,
        "LANGFUSE_RELEASE": config.LANGFUSE_RELEASE,
    }
    for key, value in values.items():
        if value:
            os.environ[key] = value


if config.LANGFUSE_ENABLED:
    _bridge_environment()
    from langfuse import get_client, observe, propagate_attributes

    @contextmanager
    def trace_attributes(**attributes):
        with propagate_attributes(**attributes):
            yield

    @contextmanager
    def observation(*, name: str, as_type: str = "span", **fields):
        with get_client().start_as_current_observation(
            name=name, as_type=as_type, **fields
        ) as current:
            yield current

    def update_span(**fields) -> None:
        get_client().update_current_span(**fields)

    def score_trace(name: str, value, comment: str | None = None) -> None:
        kwargs = {"name": name, "value": value}
        if comment is not None:
            kwargs["comment"] = comment
        get_client().score_current_trace(**kwargs)

    def flush() -> None:
        get_client().flush()

    def langfuse_client():
        return get_client()

    def langchain_callback():
        """Return Langfuse's LangChain/LangGraph callback for one invocation."""
        from langfuse.langchain import CallbackHandler
        return CallbackHandler()

else:
    def observe(name=None, **decorator_options):
        def decorator(function):
            @wraps(function)
            def wrapper(*args, **kwargs):
                return function(*args, **kwargs)
            return wrapper
        return decorator

    @contextmanager
    def trace_attributes(**attributes):
        yield

    @contextmanager
    def observation(*, name: str, as_type: str = "span", **fields):
        yield None

    def update_span(**fields) -> None:
        return None

    def score_trace(name: str, value, comment: str | None = None) -> None:
        return None

    def flush() -> None:
        return None

    def langfuse_client():
        return None

    def langchain_callback():
        return None
