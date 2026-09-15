"""Thin Airflow 3 DAG. Application dependencies live in a separate Python venv."""
from datetime import timedelta
import os
import shlex

import pendulum
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator


with DAG(
    dag_id="arxiv_daily",
    description="Checkpointed discovery, fixed-budget processing, audit and notification",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    schedule="15 7 * * *",  # 07:15 UTC; not the laptop's local timezone.
    catchup=False,
    max_active_runs=1,
    max_active_tasks=1,
    is_paused_upon_creation=True,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=5)},
    tags=["arxiv", "scientific-papers"],
) as dag:
    def command(stage, **kwargs):
        return BashOperator(
            task_id=stage,
            bash_command=(f"exec {shlex.quote(os.getenv('PAPERS_PYTHON', '/opt/rag/.venv/bin/python'))} "
                          f'-m src.api.papers.schedule {stage} --run-date "$PAPERS_RUN_DATE"'),
            # Use the actual DAG start day, not Airflow's previous interval/logical date.
            # All tasks/retries in this run use the same day. Historical paid replay is rejected.
            env={"PAPERS_RUN_DATE": "{{ dag_run.start_date.strftime('%Y-%m-%d') }}",
                 "PYTHONPATH": os.getenv("PAPERS_APP_DIR", "/opt/rag")},
            append_env=True,
            cwd=os.getenv("PAPERS_APP_DIR", "/opt/rag"),
            do_xcom_push=False,
            execution_timeout=timedelta(hours=2),
            **kwargs,
        )

    discover = command("discover")
    process = command("process")
    audit = command("audit", trigger_rule="all_done")
    # Report is the leaf and exits nonzero for ANY unsuccessful upstream stage.
    # An all_done audit must never turn a failed ingestion DAG green.
    report = command("report", trigger_rule="all_done")
    discover >> process >> audit >> report
