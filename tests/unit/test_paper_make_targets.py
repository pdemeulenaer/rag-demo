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
