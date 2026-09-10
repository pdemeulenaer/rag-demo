"""Check Make recipes without starting services, networking or ingesting papers."""
from pathlib import Path
import shlex
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]


def dry_run(target, *overrides):
    result = subprocess.run(
        ["make", "--no-print-directory", "--dry-run", target, "DAYS=", "UNTIL=", "LIMIT=", *overrides],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    return shlex.split(result.stdout)


@pytest.mark.parametrize("target,command", [
    ("papers-scope", "scope"),
    ("papers-init-db", "init-db"),
    ("papers-backfill", "backfill"),
    ("papers-process", "process"),
    ("papers-sync", "sync"),
    ("papers-daily", "daily"),
    ("papers-status", "status"),
    ("papers-audit", "audit"),
])
def test_host_commands_preserve_cli_defaults(target, command):
    assert dry_run(target) == ["uv", "run", "python", "-m", "src.api.papers", command]


def test_preview_is_always_metadata_only():
    assert dry_run("papers-preview", "DAYS=3", "UNTIL=2026-09-01") == [
        "uv", "run", "python", "-m", "src.api.papers", "backfill", "--dry-run",
        "--days", "3", "--until", "2026-09-01",
    ]


@pytest.mark.parametrize("target,command", [("papers-process", "process"), ("papers-daily", "daily")])
def test_processing_limit_is_forwarded(target, command):
    assert dry_run(target, "LIMIT=2") == [
        "uv", "run", "python", "-m", "src.api.papers", command, "--limit", "2",
    ]


def test_db_start_is_separate_and_waits_for_health():
    assert dry_run("papers-db-up") == [
        "docker", "compose", "--profile", "papers", "up", "-d", "--wait", "postgres",
    ]


def test_import_requires_explicit_model_confirmation():
    assert dry_run("papers-import-uploads", "LEGACY_MODEL=text-embedding-3-small") == [
        "uv", "run", "python", "-m", "src.api.papers", "import-uploads",
        "--legacy-embedding-model", "text-embedding-3-small",
    ]


def test_scheduled_runner_and_read_only_status():
    assert dry_run("papers-scheduled", "LIMIT=2", "RUN_DATE=2026-09-10") == [
        "uv", "run", "python", "-m", "src.api.papers.schedule", "all",
        "--run-date", "2026-09-10", "--limit", "2",
    ]
    assert dry_run("papers-run-status", "RUN_DATE=2026-09-10") == [
        "uv", "run", "python", "-m", "src.api.papers.schedule", "status", "--run-date", "2026-09-10",
    ]


def test_airflow_start_does_not_unpause_or_trigger_dag():
    command = dry_run("airflow-up")
    assert "--profile" in command and "airflow" in command
    assert "unpause" not in command and "trigger" not in command


@pytest.mark.parametrize("target,action", [("papers-backup", "backup"), ("papers-backups", "list"),
                                         ("papers-backup-check", "check")])
def test_backup_commands_need_no_app_dependencies(target, action):
    assert dry_run(target) == ["python3", "scripts/papers_backup.py", action]
