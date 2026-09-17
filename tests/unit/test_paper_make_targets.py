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
    ("papers-reindex", "reindex"),
    ("papers-sync", "sync"),
    ("papers-daily", "daily"),
    ("papers-status", "status"),
    ("papers-count", "count"),
    ("papers-audit", "audit"),
])
def test_host_commands_preserve_cli_defaults(target, command):
    assert dry_run(target) == ["uv", "run", "python", "-m", "src.api.papers", command]


def test_evaluation_make_preview_and_paid_generation_are_separate():
    assert dry_run("eval-preview", "EVAL_DIR=data/evaluation/my pilot", "QUESTIONS=10", "PAPERS=20") == [
        "uv", "run", "python", "-m", "evals.generate_questions", "prepare",
        "--output", "data/evaluation/my pilot", "--source", "arxiv", "--questions", "10",
        "--papers", "20", "--seed", "42", "--model", "gpt-4.1-mini",
        "--max-completion-tokens", "2500",
    ]
    assert dry_run("create-eval-dataset", "EVAL_DIR=data/evaluation/my pilot") == [
        "uv", "run", "python", "-m", "evals.generate_questions", "generate",
        "--output", "data/evaluation/my pilot",
    ]


def test_evaluation_make_forwards_custom_model_and_token_budget():
    command = dry_run("eval-preview", "EVAL_MODEL=gpt-5", "EVAL_MAX_TOKENS=25000")
    assert command[-4:] == ["--model", "gpt-5", "--max-completion-tokens", "25000"]


def test_evaluation_make_forwards_optional_reasoning_effort():
    command = dry_run("eval-preview", "EVAL_MODEL=gpt-5-mini", "EVAL_REASONING_EFFORT=minimal")
    assert command[-6:] == ["--model", "gpt-5-mini", "--reasoning-effort", "minimal",
                            "--max-completion-tokens", "2500"]


def test_evaluation_make_forwards_agentic_question_profiles():
    command = dry_run("eval-preview", "QUESTIONS=70", "EVAL_SINGLE_FACT=20",
                      "EVAL_SINGLE_SYNTHESIS=10", "EVAL_CROSS_COMPARISON=15",
                      "EVAL_CROSS_MULTIHOP=10", "EVAL_METADATA_DISCOVERY=5",
                      "EVAL_UNANSWERABLE=10")
    assert command[-12:] == [
        "--single-fact", "20", "--single-synthesis", "10",
        "--cross-comparison", "15", "--cross-multihop", "10",
        "--metadata-discovery", "5", "--unanswerable", "10",
    ]


def test_evaluation_connectivity_check_is_not_generation():
    assert dry_run("eval-check", "EVAL_DIR=data/evaluation/gpt5") == [
        "uv", "run", "python", "-m", "evals.generate_questions", "check",
        "--output", "data/evaluation/gpt5",
    ]


def test_reviewed_evaluation_runner_forwards_modes_and_optional_limit():
    command = dry_run("eval-run", "EVAL_DIR=data/evaluation/reviewed",
                      "EVAL_MODES=vanilla hybrid", "EVAL_LIMIT=3", "EVAL_JUDGE=true")
    assert command == [
        "uv", "run", "python", "-m", "evals.run_benchmark",
        "--dataset", "data/evaluation/reviewed/questions.reviewed.json",
        "--output-root", "data/evaluation/runs", "--modes", "vanilla", "hybrid",
        "--split", "all", "--top-k", "5", "--judge",
        "--judge-model", "gpt-5-mini", "--judge-reasoning-effort", "minimal",
        "--concurrency", "1", "--limit", "3",
    ]


def test_evaluation_runner_forwards_question_id_filter():
    command = dry_run("eval-run", "EVAL_QUESTION_ID=q0033")
    assert command[-2:] == ["--question-id", "q0033"]


def test_evaluation_review_validation_and_split_are_local_commands():
    assert dry_run("eval-validate", "EVAL_DIR=data/evaluation/reviewed", "EVAL_SPLIT=test") == [
        "uv", "run", "python", "-m", "evals.review_dataset", "validate",
        "--dataset", "data/evaluation/reviewed/questions.reviewed.json", "--split", "test",
    ]
    assert dry_run("eval-split", "EVAL_DIR=data/evaluation/reviewed",
                   "EVAL_SPLIT_OUTPUT=data/evaluation/reviewed/questions.v2.json") == [
        "uv", "run", "python", "-m", "evals.review_dataset", "assign-splits",
        "--dataset", "data/evaluation/reviewed/questions.reviewed.json",
        "--output", "data/evaluation/reviewed/questions.v2.json",
        "--test-ratio", "0.25", "--seed", "42",
    ]


def test_background_generation_wait_and_explicit_retry_are_forwarded():
    command = dry_run("create-eval-dataset", "EVAL_WAIT_SECONDS=300", "RETRY_JOB=q0002")
    assert command[-4:] == ["--wait-seconds", "300", "--retry-job", "q0002"]


def test_preview_is_always_metadata_only():
    assert dry_run("papers-preview", "DAYS=3", "UNTIL=2026-09-01") == [
        "uv", "run", "python", "-m", "src.api.papers", "backfill", "--dry-run",
        "--days", "3", "--until", "2026-09-01",
    ]


def test_reindex_preview_and_paid_limit():
    assert dry_run("papers-reindex-preview") == ["uv", "run", "python", "-m", "src.api.papers", "reindex", "--dry-run"]
    assert dry_run("papers-reindex", "LIMIT=50")[-3:] == ["reindex", "--limit", "50"]
    assert dry_run("papers-extract-preview", "PDF=paper with spaces.pdf", "EXTRACT_DIR=data/new preview") == [
        "uv", "run", "python", "-m", "src.api.papers.extraction", "--pdf", "paper with spaces.pdf",
        "--output", "data/new preview"]


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
    assert "Airflow UI: http://localhost:8080" in " ".join(command)


def test_airflow_password_reads_generated_credentials():
    assert dry_run("airflow-password") == [
        "docker", "compose", "--profile", "airflow", "exec", "airflow", "cat",
        "/opt/airflow/simple_auth_manager_passwords.json.generated",
    ]


def test_langfuse_start_uses_repo_compose_stack_and_waits():
    assert dry_run("langfuse-up") == [
        "docker", "compose", "-f", "docker-compose.yml", "-f",
        "docker-compose.langfuse.yaml", "up", "-d", "--wait",
        "langfuse-web", "langfuse-worker",
    ]


def test_langfuse_stop_preserves_volumes():
    command = dry_run("langfuse-stop")
    assert "-v" not in command
    assert "down" not in command
    assert command.count("langfuse-web") == 2


@pytest.mark.parametrize("target,action", [("papers-backup", "backup"), ("papers-backups", "list"),
                                         ("papers-backup-check", "check")])
def test_backup_commands_need_no_app_dependencies(target, action):
    assert dry_run(target) == ["python3", "scripts/papers_backup.py", action]
