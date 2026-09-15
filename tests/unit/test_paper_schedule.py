"""Offline scheduler contracts; no network, notifications, scheduler or model calls."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import runpy
import sys
from types import ModuleType
from unittest.mock import Mock

import httpx
import pytest
from sqlalchemy import inspect

from src.api.papers.arxiv import Paper
from src.api.papers.catalogue import Catalogue
from src.api.papers.schedule import MonitoringRequired, Runtime, ScheduleSettings, StageFailed, Workflow, main, notify
from src.api.papers.schedule_store import RunStore, daily_runs
from src.api.papers.settings import PaperSettings


@pytest.fixture
def setup(tmp_path):
    settings = PaperSettings(_env_file=None, PAPERS_DATABASE_URL=f"sqlite:///{tmp_path}/catalogue.db")
    catalogue = Catalogue(settings.PAPERS_DATABASE_URL)
    catalogue.initialize()
    for number in range(4):
        catalogue.discover(Paper(f"2609.{number:05d}", 1, f"Star clusters {number}", "", [],
            ["astro-ph.GA"], "2026", "2026"), settings)
    yield catalogue, settings
    catalogue.close()


def workflow(setup, limit=2):
    return Workflow(*setup, "2026-09-10", limit, 2)


def succeed(catalogue, build):
    catalogue.start(build["id"])
    # Verification itself is tested against local Qdrant elsewhere.
    catalogue.activate(build, {"chunk_count": 1})


def test_additive_migration_and_missing_run_table(setup):
    catalogue, settings = setup
    before = catalogue.all_builds()
    daily_runs.drop(catalogue.engine)
    with pytest.raises(RuntimeError, match="init-db"):
        RunStore(catalogue)
    catalogue.initialize()
    catalogue.initialize()
    assert "paper_daily_runs" in inspect(catalogue.engine).get_table_names()
    assert catalogue.all_builds() == before
    assert catalogue.checkpoint("schema_version") == "2"


def test_fixed_plan_survives_restart_and_does_not_refill_after_success(setup):
    catalogue, settings = setup
    run = workflow(setup)
    discovery = Mock(return_value=4)
    run.discover(discovery)
    selected = run.state["build_ids"][:]
    calls = []

    def partial(build):
        calls.append(build["id"])
        if build["id"] == selected[1] and calls.count(build["id"]) == 1:
            raise RuntimeError("first attempt fails")
        succeed(catalogue, build)

    with pytest.raises(StageFailed):
        run.process(partial)
    # New connections/process instance still see exactly the original plan.
    other = Catalogue(settings.PAPERS_DATABASE_URL)
    try:
        retry = workflow((other, settings))
        retry.discover(discovery)
        retry.process(partial)
        assert retry.state["build_ids"] == selected
        assert calls == [selected[0], selected[1], selected[1]]
        assert len(catalogue.pending(settings, 10)) == 2
        retry.process(partial)
        assert len(calls) == 3
        discovery.assert_called_once()
    finally:
        other.close()


def test_attempts_are_bounded_even_on_repeated_task_clear(setup):
    run = workflow(setup, limit=1)
    run.discover(lambda: 0)
    fail = Mock(side_effect=RuntimeError("cannot index"))
    for _ in range(5):
        with pytest.raises(StageFailed):
            run.process(fail)
    assert fail.call_count == 2
    assert sum(run.state["attempts"].values()) == 2


def test_interruption_consumes_attempt_before_model_work(setup):
    run = workflow(setup, limit=1)
    run.discover(lambda: 0)
    with pytest.raises(KeyboardInterrupt):
        run.process(Mock(side_effect=KeyboardInterrupt))
    restarted = workflow(setup, limit=1)
    assert list(restarted.state["attempts"].values()) == [1]
    restarted.process(lambda build: succeed(setup[0], build))
    assert list(restarted.state["attempts"].values()) == [2]


def test_plan_configuration_cannot_expand_on_retry(setup):
    workflow(setup)
    with pytest.raises(ValueError, match="immutable"):
        workflow(setup, limit=3)


def test_audit_success_does_not_hide_processing_failure(setup):
    run = workflow(setup, limit=1)
    run.discover(lambda: 0)
    with pytest.raises(StageFailed):
        run.process(Mock(side_effect=RuntimeError))
    run.audit(lambda: {"ok": True})
    alert = Mock()
    with pytest.raises(StageFailed):
        run.report(alert)
    summary = alert.call_args.args[0]
    assert summary["ok"] is False
    assert summary["stages"] == {"discover": "success", "process": "failed", "audit": "success"}
    assert summary["not_completed"] == 1
    assert run.store.get(run.state["id"])["status"] == "failed"


def test_retry_invalidates_previous_audit(setup):
    run = workflow(setup, limit=1)
    run.discover(lambda: 0)
    with pytest.raises(StageFailed):
        run.process(Mock(side_effect=RuntimeError))
    run.audit(lambda: {"ok": True})
    run.process(lambda b: succeed(setup[0], b))
    with pytest.raises(StageFailed):
        run.report(Mock())
    run.audit(lambda: {"ok": True})
    assert run.report(Mock())["ok"] is True


def test_failed_audit_and_notification_are_reported(setup):
    run = workflow(setup, limit=1)
    run.discover(lambda: 0)
    run.process(lambda b: succeed(setup[0], b))
    with pytest.raises(StageFailed):
        run.audit(lambda: {"ok": False, "unregistered_points": ["orphan"]})
    with pytest.raises(StageFailed, match="Notification"):
        run.report(Mock(side_effect=RuntimeError("secret endpoint")))
    saved = run.store.get(run.state["id"])
    assert saved["status"] == "failed"
    assert saved["notification"] == {"status": "failed", "error": "RuntimeError"}
    assert "secret endpoint" not in str(saved)


def test_zero_matching_work_is_a_successful_daily_run(setup):
    catalogue, settings = setup
    settings.ARXIV_TOPIC_TERMS = "no matches"
    run = workflow(setup)
    run.discover(lambda: 0)
    process = Mock()
    run.process(process)
    run.audit(lambda: {"ok": True})
    assert run.report(Mock())["selected"] == 0
    process.assert_not_called()


def test_monitoring_contract_sends_failure_json_or_success_heartbeat():
    settings = ScheduleSettings(_env_file=None, PAPERS_ALERT_WEBHOOK_URL="https://example.test/failure",
                                PAPERS_HEARTBEAT_URL="https://example.test/ping")
    seen = []
    def handle(request):
        seen.append(request)
        return httpx.Response(200)
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        notify({"ok": False, "run_id": "test"}, settings, client)
        notify({"ok": True, "run_id": "test"}, settings, client)
    assert [r.method for r in seen] == ["POST", "GET"]
    assert seen[0].url.path == "/failure"
    assert seen[1].url.path == "/ping"
    with pytest.raises(MonitoringRequired):
        notify({"ok": True}, ScheduleSettings(_env_file=None, PAPERS_REQUIRE_MONITORING=True))


def test_cli_all_audits_and_reports_after_discovery_error(setup, monkeypatch):
    catalogue, settings = setup
    import src.api.papers.schedule as schedule
    monkeypatch.setattr(schedule, "PaperSettings", lambda: settings)
    monkeypatch.setattr(schedule, "ScheduleSettings", lambda: ScheduleSettings(_env_file=None,
        PAPERS_ALERT_WEBHOOK_URL="https://example.test/fail", PAPERS_HEARTBEAT_URL="https://example.test/ping"))
    runtime = Mock()
    runtime.discover.side_effect = RuntimeError("secret")
    runtime.audit.return_value = {"ok": True}
    monkeypatch.setattr(schedule, "Runtime", lambda *args: runtime)
    alert = Mock()
    monkeypatch.setattr(schedule, "notify", alert)
    assert main(["all"]) == 1
    runtime.process.assert_not_called()
    runtime.audit.assert_called_once()
    assert alert.call_args.args[0]["ok"] is False


def test_cli_rejects_unmonitored_strict_or_historical_paid_run(setup, monkeypatch, capsys):
    import src.api.papers.schedule as schedule
    monkeypatch.setattr(schedule, "PaperSettings", lambda: setup[1])
    monkeypatch.setattr(schedule, "ScheduleSettings", lambda: ScheduleSettings(_env_file=None, PAPERS_REQUIRE_MONITORING=True))
    runtime = Mock()
    monkeypatch.setattr(schedule, "Runtime", runtime)
    assert main(["discover"]) == 1
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
    assert main(["process", "--run-date", yesterday]) == 1
    runtime.assert_not_called()
    output = capsys.readouterr().out
    assert "command_failed" in output
    assert "PAPERS_REQUIRE_MONITORING=true requires both" in output


def test_cli_allows_discovery_without_monitoring_by_default(setup, monkeypatch, capsys):
    import src.api.papers.schedule as schedule
    monkeypatch.setattr(schedule, "PaperSettings", lambda: setup[1])
    monkeypatch.setattr(schedule, "ScheduleSettings", lambda: ScheduleSettings(_env_file=None))
    runtime = Mock()
    runtime.discover.return_value = 0
    monkeypatch.setattr(schedule, "Runtime", lambda *args: runtime)
    assert main(["discover"]) == 0
    runtime.discover.assert_called_once()
    output = capsys.readouterr().out
    assert "monitoring_optional" in output and "WARNING" in output


@pytest.mark.parametrize("success", [True, False])
def test_missing_optional_notifications_do_not_change_ingestion_outcome(setup, monkeypatch, success):
    run = workflow(setup, limit=1)
    run.discover(lambda: 0)
    if success:
        run.process(lambda build: succeed(setup[0], build))
    else:
        with pytest.raises(StageFailed):
            run.process(Mock(side_effect=RuntimeError))
    run.audit(lambda: {"ok": True})
    monkeypatch.setattr("src.api.papers.schedule.httpx.Client", Mock(side_effect=AssertionError("No network allowed")))
    notifier = lambda summary: notify(summary, ScheduleSettings(_env_file=None))
    if success:
        assert run.report(notifier)["ok"] is True
    else:
        with pytest.raises(StageFailed, match="Daily workflow failed"):
            run.report(notifier)
    saved = run.store.get(run.state["id"])
    assert saved["notification"]["status"] == "skipped"
    assert saved["notification"]["reason"] == "not_configured"
    assert saved["status"] == ("success" if success else "failed")


def test_partially_configured_monitoring_sends_only_configured_endpoint():
    settings = ScheduleSettings(_env_file=None, PAPERS_ALERT_WEBHOOK_URL="https://example.test/failure")
    client = Mock()
    assert notify({"ok": True}, settings, client) is False
    client.get.assert_not_called()
    assert notify({"ok": False}, settings, client) is True
    client.post.assert_called_once()


def test_configured_notification_delivery_errors_still_fail():
    settings = ScheduleSettings(_env_file=None, PAPERS_HEARTBEAT_URL="https://example.test/ping")
    client = Mock()
    client.get.side_effect = httpx.ConnectError("unreachable")
    with pytest.raises(httpx.ConnectError):
        notify({"ok": True}, settings, client)


def test_dag_is_paused_serial_and_reports_after_failures(monkeypatch):
    """Load DAG with lightweight API doubles; real import checked by airflow-check."""
    tasks = {}
    class DAG:
        def __init__(self, **kwargs): self.kwargs = kwargs
        def __enter__(self): return self
        def __exit__(self, *args): pass
    class Operator:
        def __init__(self, **kwargs):
            self.kwargs, self.children = kwargs, []
            tasks[kwargs["task_id"]] = self
        def __rshift__(self, other):
            self.children.append(other.kwargs["task_id"])
            return other
    for name in ["airflow", "airflow.sdk", "airflow.providers", "airflow.providers.standard",
                 "airflow.providers.standard.operators", "airflow.providers.standard.operators.bash", "pendulum"]:
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    sys.modules["airflow.sdk"].DAG = DAG
    sys.modules["airflow.providers.standard.operators.bash"].BashOperator = Operator
    sys.modules["pendulum"].datetime = lambda *args, **kwargs: "UTC-start"
    namespace = runpy.run_path(str(Path(__file__).resolve().parents[2] / "dags/arxiv_daily.py"))
    config = namespace["dag"].kwargs
    assert config["is_paused_upon_creation"] is True
    assert config["catchup"] is False
    assert config["max_active_runs"] == config["max_active_tasks"] == 1
    assert config["schedule"] == "15 7 * * *"
    assert tasks["discover"].children == ["process"]
    assert tasks["process"].children == ["audit"]
    assert tasks["audit"].children == ["report"]
    assert tasks["audit"].kwargs["trigger_rule"] == tasks["report"].kwargs["trigger_rule"] == "all_done"
    assert "dag_run.start_date" in tasks["process"].kwargs["env"]["PAPERS_RUN_DATE"]
    assert all(t.kwargs["execution_timeout"] == timedelta(hours=2) for t in tasks.values())


def test_runtime_reuses_arxiv_rate_limiter(setup, monkeypatch):
    factory = Mock()
    monkeypatch.setattr("src.api.papers.schedule.ArxivClient", factory)
    runtime = Runtime(*setup)
    assert runtime.arxiv() is runtime.arxiv()
    factory.assert_called_once()
    runtime.close()
    factory.return_value.close.assert_called_once()
