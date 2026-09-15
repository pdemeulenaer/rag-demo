"""Durable daily plans. All mutations require the catalogue's existing writer lock."""
from copy import deepcopy
from datetime import date

from sqlalchemy import Column, JSON, MetaData, String, Table, insert, inspect, select, update

from .catalogue import now

run_schema = MetaData()
daily_runs = Table("paper_daily_runs", run_schema,
    Column("id", String, primary_key=True),
    Column("state", JSON, nullable=False),
    Column("updated_at", String, nullable=False))


class RunStore:
    def __init__(self, catalogue):
        self.catalogue = catalogue
        self.engine = catalogue.engine
        if not inspect(self.engine).has_table("paper_daily_runs"):
            raise RuntimeError("Run make papers-init-db to add the daily-run table")

    def get(self, run_id):
        with self.engine.connect() as connection:
            return connection.execute(select(daily_runs.c.state).where(daily_runs.c.id == run_id)).scalar()

    def save(self, state):
        state["updated_at"] = now()
        with self.engine.begin() as connection:
            connection.execute(update(daily_runs).where(daily_runs.c.id == state["id"]).values(
                state=deepcopy(state), updated_at=state["updated_at"]))

    def ensure(self, run_id, settings, limit, attempts):
        if date.fromisoformat(run_id).isoformat() != run_id:
            raise ValueError("Run ID must be a canonical UTC date")
        if not 1 <= limit <= 100 or not 1 <= attempts <= 3:
            raise ValueError("Invalid run budget")
        config = {"scope_id": settings.scope_id, "pipeline_id": settings.pipeline_id,
            "limit": limit, "attempt_limit": attempts, "max_pdf_mb": settings.ARXIV_MAX_PDF_MB,
            "max_chunks": settings.ARXIV_MAX_CHUNKS, "build_attempt_limit": settings.ARXIV_MAX_ATTEMPTS}
        state = self.get(run_id)
        if state:
            if state["config"] != config:
                raise ValueError("Daily plan configuration is immutable; restore original settings")
            return state
        state = {"id": run_id, "config": config, "created_at": now(), "updated_at": now(),
            "build_ids": None, "attempts": {}, "stages": {}, "status": "pending"}
        with self.engine.begin() as connection:
            connection.execute(insert(daily_runs).values(id=run_id, state=state, updated_at=state["updated_at"]))
        return state
