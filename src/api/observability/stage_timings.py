"""Request-local retrieval timings, including failures and parallel native tools.

Durations sum work across calls; parallel calls can exceed wall-clock retrieval.
This module is configuration/provider independent and never logs request content.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic


@dataclass
class _Collector:
    values: dict[str, float]
    lock: Lock = field(default_factory=Lock)


_current: ContextVar[_Collector | None] = ContextVar("retrieval_stage_timings", default=None)


@contextmanager
def collect_stage_timings(values: dict[str, float]):
    """Context propagation shares a locked sink within one benchmark item only."""
    token = _current.set(_Collector(values))
    try:
        yield
    finally:
        _current.reset(token)


def record_stage_seconds(name: str, seconds: float) -> None:
    collector = _current.get()
    if collector is not None:
        with collector.lock:
            collector.values[name] = round(collector.values.get(name, 0.0) + max(0.0, seconds), 6)


@contextmanager
def measure_stage(name: str):
    started = monotonic()
    try:
        yield
    finally:
        record_stage_seconds(name, monotonic() - started)
