"""Scheduler-independent daily workflow. No scheduling or paid work at import time.

Usage: python -m src.api.papers.schedule discover|process|audit|report|all|status
"""
import argparse
from contextlib import ExitStack, closing
from datetime import date, datetime, timezone
import json

import httpx
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .arxiv import ArxivClient
from .catalogue import Catalogue, now
from .schedule_store import RunStore
from .settings import PaperSettings


class ScheduleSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    PAPERS_RUN_MAX_ATTEMPTS: int = Field(2, ge=1, le=3)
    PAPERS_REQUIRE_MONITORING: bool = False
    PAPERS_ALERT_WEBHOOK_URL: SecretStr = SecretStr("")
    PAPERS_HEARTBEAT_URL: SecretStr = SecretStr("")

    @field_validator("PAPERS_ALERT_WEBHOOK_URL", "PAPERS_HEARTBEAT_URL")
    @classmethod
    def https_only(cls, value):
        if value.get_secret_value() and not value.get_secret_value().startswith("https://"):
            raise ValueError("Monitoring endpoints must use HTTPS")
        return value


class StageFailed(RuntimeError):
    pass


class MonitoringRequired(ValueError):
    pass


def emit(event, **values):
    print(json.dumps({"event": event, "time": now(), **values}), flush=True)


def check_monitoring(settings):
    missing = [key for key in ("PAPERS_ALERT_WEBHOOK_URL", "PAPERS_HEARTBEAT_URL")
               if not getattr(settings, key).get_secret_value()]
    if missing and settings.PAPERS_REQUIRE_MONITORING:
        raise MonitoringRequired("Required monitoring endpoints are missing")
    if missing:
        emit("monitoring_optional", level="WARNING", missing_settings=missing,
             hint="Continuing without these external notifications; inspect Airflow logs and papers-run-status.")


def notify(summary, settings, client=None):
    """Generic JSON webhook on failure; dead-man heartbeat only on complete success.

    No redirects: credentials embedded in monitoring URLs must not leak to another host.
    The external heartbeat service must independently alert when pings stop.
    """
    endpoint = "PAPERS_HEARTBEAT_URL" if summary["ok"] else "PAPERS_ALERT_WEBHOOK_URL"
    url = getattr(settings, endpoint).get_secret_value()
    if not url:
        if settings.PAPERS_REQUIRE_MONITORING:
            raise MonitoringRequired("Required monitoring endpoint is missing")
        emit("notification_skipped", level="WARNING", run_id=summary.get("run_id"),
             missing_setting=endpoint, reason="not_configured")
        return False
    with ExitStack() as stack:
        client = client or stack.enter_context(httpx.Client(timeout=15, follow_redirects=False))
        response = client.get(url) if summary["ok"] else client.post(url, json=summary)
        response.raise_for_status()
    return True


class Workflow:
    def __init__(self, catalogue, settings, run_id, limit, attempts):
        self.catalogue, self.settings = catalogue, settings
        self.store = RunStore(catalogue)
        self.state = self.store.ensure(run_id, settings, limit, attempts)

    def stage(self, name, action):
        entry = self.state["stages"].get(name, {})
        if entry.get("status") == "success" and name != "audit":
            return
        if name in {"discover", "process"}:
            self.state["stages"].pop("audit", None)
            self.state.pop("audit", None)
        self.state.pop("summary", None)
        self.state.pop("notification", None)
        self.state["status"] = "running"
        self.state["stages"][name] = {"status": "running", "started_at": now()}
        self.store.save(self.state)
        emit("stage_started", run_id=self.state["id"], stage=name)
        try:
            result = action()
            self.state["stages"][name].update(status="success", result=result)
        except Exception as exc:
            self.state["stages"][name].update(status="failed", error=type(exc).__name__)
            raise
        finally:
            self.state["stages"][name]["finished_at"] = now()
            self.store.save(self.state)
            emit("stage_finished", run_id=self.state["id"], stage=name,
                 status=self.state["stages"][name]["status"])

    def discover(self, discover):
        def action():
            if self.state["build_ids"] is not None:
                return {"recovered_plan": True}
            count = discover()
            self.state["build_ids"] = [b["id"] for b in self.catalogue.pending(
                self.settings, self.state["config"]["limit"])]
            self.state["discovered"] = count
            self.store.save(self.state)  # Freeze IDs before any model call.
            return {"discovered": count, "selected": len(self.state["build_ids"])}
        self.stage("discover", action)

    def process(self, process):
        def action():
            if self.state["stages"].get("discover", {}).get("status") != "success":
                raise StageFailed("Discovery did not succeed")
            failures = []
            eligible = {b["id"] for b in self.catalogue.pending(self.settings, 1000000)}
            for build_id in self.state["build_ids"]:
                build = self.catalogue.get_build(build_id)
                if build and build["status"] == "ready":
                    continue  # Also recovers a crash just after SQL activation.
                used = self.state["attempts"].get(build_id, 0)
                if build_id not in eligible or used >= self.state["config"]["attempt_limit"]:
                    failures.append(build_id)
                    continue
                self.state["attempts"][build_id] = used + 1
                self.store.save(self.state)  # An interrupted attempt still consumes its budget.
                emit("build_started", run_id=self.state["id"], build_id=build_id, attempt=used + 1)
                try:
                    process(build)
                except Exception as exc:
                    self.catalogue.fail(build_id, type(exc).__name__)
                current = self.catalogue.get_build(build_id)
                if not current or current["status"] != "ready":
                    failures.append(build_id)
                emit("build_finished", run_id=self.state["id"], build_id=build_id,
                     status=current["status"] if current else "missing")
            self.state["failed_build_ids"] = failures
            if failures:
                raise StageFailed("Some selected builds did not complete")
            return {"completed": len(self.state["build_ids"])}
        self.stage("process", action)

    def audit(self, audit):
        def action():
            result = audit()
            self.state["audit"] = result
            if not result["ok"]:
                raise StageFailed("Index audit failed or was inconclusive")
            return {"ok": True}
        self.stage("audit", action)

    def report(self, notifier):
        ids = self.state["build_ids"] or []
        completed = sum((self.catalogue.get_build(key) or {}).get("status") == "ready" for key in ids)
        ok = all(self.state["stages"].get(s, {}).get("status") == "success" for s in ("discover", "process", "audit"))
        inventory = self.catalogue.inventory("arxiv")
        summary = {"run_id": self.state["id"], "ok": ok,
            "discovered": self.state.get("discovered", 0), "selected": len(ids),
            "completed": completed, "not_completed": len(ids) - completed,
            "attempts_used": sum(self.state["attempts"].values()),
            "backlog": sum(row["status"] != "ready" for row in inventory),
            "failed_builds_total": sum(row["status"] == "failed" for row in inventory),
            "stages": {key: value["status"] for key, value in self.state["stages"].items()}}
        self.state.update(status="success" if ok else "failed", summary=summary, finished_at=now())
        self.store.save(self.state)
        emit("run_summary", **summary)
        try:
            delivered = notifier(summary)
        except Exception as exc:
            self.state["notification"] = {"status": "failed", "error": type(exc).__name__}
            self.store.save(self.state)
            raise StageFailed("Notification delivery failed") from None
        self.state["notification"] = {"status": "skipped" if delivered is False else "sent", "time": now()}
        if delivered is False:
            self.state["notification"]["reason"] = "not_configured"
        self.store.save(self.state)
        if not ok:
            raise StageFailed("Daily workflow failed; see saved summary")
        return summary


class Runtime:
    """Lazy service clients: audit/report never instantiate the embedding client."""
    def __init__(self, catalogue, settings):
        self.catalogue, self.settings = catalogue, settings
        self._arxiv = None

    def arxiv(self):
        # Reuse the client so its request-spacing limiter survives between papers.
        if self._arxiv is None:
            self._arxiv = ArxivClient(self.settings.ARXIV_USER_AGENT)
        return self._arxiv

    def close(self):
        if self._arxiv:
            self._arxiv.close()

    def discover(self):
        from .ingestion import discover_daily
        return discover_daily(self.arxiv(), self.catalogue, self.settings)

    def process(self, build):
        from openai import OpenAI
        from .artifacts import ArtifactStore
        from .ingestion import PaperIndexer, process_pending
        from .uploads import qdrant_client
        from src.api.core.config import config
        if self.settings.PAPERS_COLLECTION == config.QDRANT_COLLECTION_NAME:
            raise ValueError("Upload and arXiv collections must differ")
        with OpenAI(api_key=config.OPENAI_API_KEY, max_retries=0, timeout=90) as embeddings, closing(qdrant_client()) as qdrant:
            def embed(texts):
                result = embeddings.embeddings.create(input=texts, model=self.settings.EMBEDDING_MODEL)
                return [item.embedding for item in sorted(result.data, key=lambda item: item.index)]
            process_pending(self.arxiv(), self.catalogue, self.settings, ArtifactStore(self.settings),
                PaperIndexer(self.settings, qdrant, embed), 1, selected_builds=[build])

    def audit(self):
        from .consistency import audit
        from .uploads import qdrant_client
        from src.api.core.config import config
        with closing(qdrant_client()) as qdrant:
            return audit(self.catalogue, qdrant, [self.settings.PAPERS_COLLECTION, config.QDRANT_COLLECTION_NAME])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["discover", "process", "audit", "report", "all", "status"])
    parser.add_argument("--run-date", type=date.fromisoformat, default=datetime.now(timezone.utc).date())
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    catalogue = runtime = None
    try:
        settings, monitoring = PaperSettings(), ScheduleSettings()
        limit = args.limit if args.limit is not None else settings.ARXIV_DAILY_LIMIT
        catalogue = Catalogue(settings.PAPERS_DATABASE_URL)
        catalogue.require_schema()
        if args.stage == "status":
            state = RunStore(catalogue).get(args.run_date.isoformat())
            print(json.dumps(state, indent=2))
            return 0 if state else 1
        # Prevent catch-up/manual dates from bypassing today's shared selection budget.
        if args.stage in {"discover", "process", "all"} and args.run_date != datetime.now(timezone.utc).date():
            raise ValueError("Cost-bearing daily runs must use today's UTC date; use explicit backfill commands for history")
        if args.stage in {"discover", "process", "all"}:
            check_monitoring(monitoring)
        with catalogue.writer_lock():
            workflow = Workflow(catalogue, settings, args.run_date.isoformat(), limit, monitoring.PAPERS_RUN_MAX_ATTEMPTS)
            runtime = Runtime(catalogue, settings)
            actions = {"discover": lambda: workflow.discover(runtime.discover),
                "process": lambda: workflow.process(runtime.process),
                "audit": lambda: workflow.audit(runtime.audit),
                "report": lambda: workflow.report(lambda summary: notify(summary, monitoring))}
            if args.stage == "all":
                failed = False
                for stage in ("discover", "process", "audit", "report"):
                    if stage == "process" and workflow.state["stages"].get("discover", {}).get("status") != "success":
                        continue
                    try:
                        actions[stage]()
                    except Exception as exc:
                        failed = True
                        emit("stage_error", run_id=workflow.state["id"], stage=stage, error=type(exc).__name__)
                return int(failed)
            actions[args.stage]()
            return 0
    except Exception as exc:
        # Exception messages can contain URLs/credentials. Only expose the class.
        hint = ("PAPERS_REQUIRE_MONITORING=true requires both PAPERS_ALERT_WEBHOOK_URL and PAPERS_HEARTBEAT_URL. "
                "Configure them, or set PAPERS_REQUIRE_MONITORING=false for local use."
                if isinstance(exc, MonitoringRequired) else
                "Check monitoring configuration, run date, saved run status, schema and service health")
        emit("command_failed", stage=args.stage, error=type(exc).__name__, hint=hint)
        return 1
    finally:
        if runtime:
            runtime.close()
        if catalogue:
            catalogue.close()


if __name__ == "__main__":
    raise SystemExit(main())
