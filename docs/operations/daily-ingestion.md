# Daily arXiv ingestion

The optional Airflow DAG runs **discovery → process → audit → report** at **07:15 UTC**.
It starts **paused**. The normal `make compose` does not start Airflow.

## Set up once

1. For local use, **leave `PAPERS_ALERT_WEBHOOK_URL` and `PAPERS_HEARTBEAT_URL` empty**.
   Monitoring is optional by default (`PAPERS_REQUIRE_MONITORING=false`); no external
   account is needed. Logs and saved run summaries remain available. Set an identifiable
   `ARXIV_USER_AGENT` with your contact address.

2. Run **`make papers-backup`** to back up PostgreSQL, then initialize and start Airflow:

    ```bash
    make papers-backup
    make papers-init-db
    make airflow-up
    make airflow-check
    ```

    Run these in order; stop if any command fails. `papers-backup` starts PostgreSQL
    if needed, creates a timestamped archive in `~/rag-demo-backups`, checks it, and
    prints its location. Use `make papers-backups` to list saved backups.
    See [backup commands](catalogue.md#backup-commands).

    `init-db` adds `paper_daily_runs` without replacing existing documents or vectors.
    `airflow-check` should show no import errors; it does not execute ingestion.

3. Open **http://localhost:8080**. For this local standalone setup, retrieve the generated
   login credentials locally (do not paste them into logs or chat):

    ```bash
    docker compose --profile airflow exec airflow cat /opt/airflow/simple_auth_manager_passwords.json.generated
    ```

4. Review `ARXIV_DAILY_LIMIT` (default **10**) and monitoring configuration. **Unpause
   `arxiv_daily` only when ready to authorize daily downloads and embedding charges.**
   Inspect its first run. If monitoring is configured, also confirm heartbeat receipt.

Only one scheduler should operate this corpus. A laptop must be awake; use an always-on
host for reliable daily execution. Disable any existing cron/other daily trigger first.
Restarting Airflow preserves the DAG's previous paused/unpaused state.

## Everyday commands

For the Markdown-extraction upgrade, pause/drain ingestion and follow the
[re-indexing instructions](../getting-started/arxiv.md#upgrade-existing-pdfs-to-markdown-extraction).
Rebuild Airflow as well as the API: an old worker must not keep producing old-extractor builds.

```bash
make papers-run-status                      # Today's saved run; no writes/model calls
make papers-run-status RUN_DATE=2026-09-10  # Historical run
make airflow-logs                           # Scheduler/task troubleshooting
make papers-audit                           # Independent read-only consistency check
make papers-count                           # Total ready documents (arXiv + uploads)
make airflow-stop                           # Stop Airflow, leaving the app running
```

`papers-count` prints one integer from the PostgreSQL catalogue: documents with an
active ready build, not chunks or pending papers. A failed replacement does not
exclude a still-active ready version. Use `papers-audit` to verify Qdrant consistency.

To run the same workflow manually **with paid processing**, use
`make papers-scheduled LIMIT=10`. It runs once; repeat with the same settings to retry
within the saved budget. This CLI works without Airflow. Do not run it concurrently
with the scheduler. The older `papers-daily`/`papers-process` commands remain explicit
manual tools and **do not participate in the scheduled-run budget**.

## Optional external alerts

Leave the two URLs empty for now: missing notifications log a warning and are recorded
as `skipped`, without blocking discovery or a successful run. Ingestion/audit failures
still fail the DAG. Configured endpoints are used; delivery failures still fail reporting.

For a monitored deployment, set `PAPERS_REQUIRE_MONITORING=true` and configure both:

- `PAPERS_ALERT_WEBHOOK_URL`: an HTTPS endpoint accepting a generic JSON failure POST.
- `PAPERS_HEARTBEAT_URL`: an HTTPS GET endpoint on an independent dead-man monitor.
  Set daily expected pings, processing grace (e.g. six hours), and an alert destination
  there. Confirm it alerts even if the first ping never arrives.

Without that external monitor, a stopped scheduler/host cannot alert you. Check Airflow
and `make papers-run-status` manually during local testing.

After changing application code or `.env`, run `make airflow-up` to rebuild/recreate
the container; a plain restart does not apply these changes. Pause the DAG first if
you do not want queued work to resume immediately. Retry failed tasks with their
downstream tasks afterward; for an old UTC run date, trigger a new run instead.

## Guarantees and limits

- One immutable plan per UTC date in the catalogue: selected build IDs, scope/pipeline,
  limits, attempt counters, stage outcomes, full audit and summary. Retrying or clearing
  an Airflow task never fills completed slots with additional papers.
- `PAPERS_RUN_MAX_ATTEMPTS=2` bounds attempts per selected build/date, also subject to the
  lifetime `ARXIV_MAX_ATTEMPTS`. An interrupted attempt consumes budget before model work.
  SDK embedding retries are disabled in this runner. This bounds processing, **not exact
  tokens/dollars**; use provider spending controls too. Ambiguous model responses may
  still incur a charge even when processing fails.
- Airflow allows one active run/task; each task has one retry after five minutes and a
  two-hour timeout. Existing PostgreSQL writer locks also serialize against GUI ingestion.
  A busy lock fails the task and can be retried; work is never run concurrently through it.
- `catchup=False`: incremental metadata checkpoints catch up after outages, without
  replaying paid daily jobs for every missed logical date. The run key uses the actual
  DAG start day in UTC, shared by all its tasks. Processing an old date is rejected,
  including retries crossing midnight; use the next day's run or explicit reviewed backfill.
- Audit runs after processing failure too. A passing audit cannot make a failed ingestion
  successful. The final report task exits nonzero unless discovery, processing and audit
  all succeeded. An empty selection is a valid successful run.
- Failure reports are JSON POSTs containing `run_id`, `ok`, `discovered`, `selected`,
  `completed`, `not_completed`, `attempts_used`, `backlog`, `failed_builds_total` and
  `stages`. `discovered` counts matched metadata records, not necessarily new papers.
  Use a compatible endpoint/adapter; this is not a Slack-specific payload.
- Only complete success sends a heartbeat GET. Notification delivery errors fail the
  report task and are recorded. Deliveries are at-least-once: deduplicate by run ID/status.
  Empty optional endpoints are skipped, not counted as delivery errors. In strict mode,
  both URLs are required before discovery/processing. Database outages or killed jobs may
  prevent a failure POST; an independently configured heartbeat monitor covers missing successes.
- `make papers-run-status` includes safe exception classes, build IDs, attempts and audit
  details. JSON events go to stdout/Airflow task logs. Logs and orchestration state persist
  in `airflow_home` and `airflow_postgres`; run records live in the existing paper database.
  No retention/deletion or automatic repair is installed. Monitor disk space and review
  exhausted/blocked builds; normal pending backlog alone is not an ingestion failure.

## Deployment and verification

Airflow uses a **separate virtual environment and metadata database**. Its dependencies
are not added to the application's `pyproject.toml`; the image pins Airflow 3.3.1 and
uses the app's existing lockfile. To reuse another Airflow **3** deployment, mount this
DAG and provide the app interpreter/code via `PAPERS_PYTHON` and `PAPERS_APP_DIR`, plus
the same database, Qdrant, artifact and monitoring settings. Do not copy it unmodified
into an Airflow 2 environment.

The bundled `standalone` container is a localhost-only demo, **not a production Airflow
deployment**. For production, separate and secure its services, use managed secrets and
persistent/shared artifacts. See the official [Airflow quick start](https://airflow.apache.org/docs/apache-airflow/3.3.1/start.html)
and [DAG-run semantics](https://airflow.apache.org/docs/apache-airflow/3.3.1/core-concepts/dag-run.html).

`make test` verifies budget persistence, crash/retry behavior, failed-stage propagation,
monitoring payloads and the DAG wiring using offline doubles. It does not execute a real
Airflow scheduler, send alerts or call models. After building, use `make airflow-check`
and inspect a deliberately authorized first run before relying on automation.
