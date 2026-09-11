# RAG Demo — project handoff

## Purpose and current shape

This is a scientific-paper RAG demo: Streamlit (`src/chatbot_ui`) calls a FastAPI backend
(`src/api`), which retrieves from Qdrant and generates answers with OpenAI or Groq.
It supports source citations, figure retrieval, Redis-backed conversation memory, and
two ingestion modes. MkDocs documentation is in `docs/`; start at
`docs/architecture/index.md` for the fuller diagrams.

## Runtime architecture

- **UI:** `src/chatbot_ui/main.py`; sends `POST /rag2` and `POST /ingest` to `API_URL`.
- **API:** `src/api/main.py`; routers are in `src/api/api/`. Legacy `POST /rag2` requests
  classify questions and route metadata intents; explicit Vanilla/Hybrid presets bypass
  classification and retrieve evidence directly.
- **RAG:** `src/api/rag/retrieval.py`: OpenAI embedding -> Qdrant RRF fusion of dense and
  full-text retrieval -> Cohere rerank -> structured OpenAI/Groq response. The model selects
  cited chunk IDs; only those sources/figures are returned.
- **Memory:** pickled `ConversationMemory` objects in Redis, per `session_id`, 10-message
  recent window plus a Groq summary; TTL is refreshed to one hour on every message.
- **Uploaded-PDF ingestion:** PDF text/figures are extracted with PyMuPDF. Text chunks, a document summary,
  and figure descriptions become staged Qdrant points. Small uploads run synchronously;
  uploads of `INGESTION_BATCH_THRESHOLD` files or more submit figure analysis to OpenAI
  Batch. `src/api/papers/uploads.py` owns their shared catalogue lifecycle. The poller
  (`src/api/ingestion/poller.py`) finishes jobs from durable PostgreSQL manifests.
- **Storage:** local figures live under `src/api/data/images`; Azure Blob storage is selectable
  with `STORAGE_MODE=AZURE`. Local image URLs use `EXTERNAL_API_URL`.
- **Deployment:** `docker-compose.yml` runs UI, API, ingestion worker, and Redis. Qdrant is
  normally external (Cloud); the local Compose service is intentionally commented out.
  PostgreSQL is required by both ingestion paths and starts with the normal stack;
  only the one-shot arXiv CLI remains under the `papers` profile.

## Configuration and decisions

- `src/api/core/config.py` (`Config`) configures the existing API/RAG/upload stack;
  `src/api/papers/settings.py` (`PaperSettings`) configures the arXiv catalogue/CLI. Secrets and
  endpoints come from `.env`/environment; defaults in that class are intentional current
  defaults. Prompt templates are YAML files under `src/api/rag/prompts/`.
- `config.yaml` is currently **not loaded by `Config`**. Treat it as legacy/experimental until
  the code is changed to consume it; do not assume its collection or model settings are active.
- Generation provider is inferred from the model name (`gpt-*`/`o1-*` => OpenAI; Groq for
  `openai/gpt-oss-*` and other names), not from `GENERATION_MODEL_PROVIDER`.
- Public `ingest_documents.py`/`worker.py` entry points delegate to `papers/uploads.py`;
  the old implementations are retained as `_..._legacy` reference functions, not the
  app's ingestion path. `ingest_documents_old.py`, `ingest_documents_now.py`, `src/api/utils.py`,
  `evals/old/`, notebooks, and `docling_trial/` are experiments/legacy references.
- Preserve both corpora: arXiv uses `PAPERS_COLLECTION`, distinct from the uploaded-PDF
  `QDRANT_COLLECTION_NAME`. Ingestion may create collections, not a Qdrant Cloud cluster;
  the managed cluster must be provisioned separately.

## Important current caveats

- `retrieval.py` uses the configured Redis host/port/database for local and Compose runs.
- New sync/Batch uploads share figure payloads (`page_number`, caption, year, build identity).
  Old indexed figures may still lack those fields; legacy adoption does not rewrite payloads.
- `ALLOW_ORIGINS` is documented but CORS is currently hard-coded to `*` in `main.py`.
- `main.py` mounts `config.IMAGES_FOLDER`, creating it if absent.
- The Makefile's `FRONTEND_IMAGE_NAME`/`BACKEND_IMAGE_NAME` values are reversed, so confirm
  actual image tags before building or pushing.
- `make docs-build` has existing missing-type warnings in `retrieval.py`.
  `make test` runs the offline pytest unit suite, not the legacy manual poller script.

## Useful commands

```bash
make compose       # local stack (recommended runtime path)
make docs-build    # validate/render MkDocs
make docs PORT=8001
make ingest        # legacy script: bypasses catalogue; do not use for the current workflow
make run-evals     # retriever evaluation; needs configured external services
```

Before changing behavior, trace the request through the router, RAG/ingestion module, and the
Qdrant payload fields together: retrieval and citation rendering depend on exact field names.

## Product direction and arXiv scope

The user's goal is a daily scientific-paper corpus and cross-paper querying, with
query-time comparison of Vanilla RAG and progressively more capable retrieval strategies
in Streamlit. Knowledge-graph RAG is a later milestone: do not add a graph database,
entity extraction or agent loop implicitly while maintaining the ingestion foundation.
The separate procurement RAG repository is an architectural reference, not the target
domain. PostgreSQL here serves paper identity, provenance and ingestion lifecycle;
it is not a reason to introduce procurement-style text-to-SQL tools.

The user selected **star-cluster papers within `astro-ph.GA`**, not the whole category
and not an automatic expansion to `astro-ph.SR`. arXiv has no dedicated star-cluster
category. `ARXIV_CATEGORIES` AND any `ARXIV_TOPIC_TERMS` phrase in title/abstract define
the scope; cross-listed categories count. Defaults include star/stellar, globular,
open, young massive and nuclear star clusters. Empty topic terms broaden selection
to the whole category. Named-cluster-only papers can be missed; galaxy clusters are
not the same topic. Keep scope changes explicit and reviewable.

## Opt-in arXiv milestone: implementation and operations

`src/api/papers/` owns the unified PostgreSQL catalogue, versioned artifacts and a
text-only arXiv processing CLI. Default scope: `astro-ph.GA` AND star-cluster phrases
in titles/abstracts. See `docs/getting-started/arxiv.md` for commands and limitations.
Metadata settings are isolated in `PaperSettings` so discovery needs no model keys.
Use `python -m src.api.papers scope`, `init-db`, `backfill`, `sync`, `process`, `daily`,
or `status`. Nothing schedules paid ingestion automatically. Only the one-shot CLI
is in the Compose `papers` profile; existing uploads retain the legacy collection
but must be registered in PostgreSQL before they are queryable.

Explicit `/rag2` modes `vanilla`/`hybrid` bypass intent routing. `corpus=arxiv` filters
Qdrant to SQL-active builds; both sources support a corpus-change fingerprint. Streamlit
exposes these presets with isolated chat context. Neither preset is agentic/graph RAG.
Hybrid is dense + full-text-constrained dense RRF with Cohere rerank, not sparse BM25.
Tests: `make test` (offline, including the frontend test; no paid calls).

### Storage and activation guarantees

- PostgreSQL is the catalogue/source of truth: `papers`, `paper_versions`,
  `paper_builds` (also the processing queue), and `paper_checkpoints`. Canonical paper,
  arXiv version and processing build IDs are distinct. Abstracts are source metadata,
  not generated summaries.
- Schema v2 renames `papers.arxiv_id` to `source_id` and adds `source` (`arxiv`/`uploads`).
  `papers-init-db` performs an idempotent migration preserving existing IDs/manifests.
  Upload identity is content-addressed: same bytes deduplicate, changed bytes are a new
  document, not a filename-based replacement. See `docs/operations/catalogue.md`.
- Build manifests record processing/model identity, artifact hashes/locations and
  verified point IDs/counts, vectors and payload identity. Only successful builds become active; failed replacements
  leave the previous active version queryable. Qdrant queries filter to SQL-active
  builds; old points are retained, not automatically deleted.
- `backfill` uses bounded submission-date Search API queries; `sync` uses incremental
  OAI-PMH metadata updates with pagination/checkpoints and overlap. Discovery queues
  work independently of PDF limits, preserving the backlog. Writes are serialized by
  a PostgreSQL advisory lock; retries are bounded by `ARXIV_MAX_ATTEMPTS`. Upload batches
  remain `waiting_batch` and unqueryable until all expected figures verify.
- Local PostgreSQL runs in its own `postgres` container, database `papers`, with
  persistent Docker volume `papers_postgres`. Host CLI: `localhost:5432`; Compose
  clients: `postgres:5432`. Do not treat container recreation as a database reset.
- Versioned PDFs/text use `data/paper_artifacts/` locally. Ephemeral deployments must
  use persistent storage, e.g. `PAPERS_STORAGE_MODE=AZURE` and a pre-created private
  `PAPERS_AZURE_CONTAINER`. This is separate from legacy figure `STORAGE_MODE` settings.

### Operator workflow

The following Make targets run the Python CLI on the **host**, except `papers-db-up`,
which starts PostgreSQL and waits for its health check. Merge settings into an existing
`.env`; never use `make env-file`/`make setup` to overwrite a configured environment.

```bash
make papers-help
make papers-scope
make papers-preview DAYS=7    # Metadata only; no DB connection/writes or embeddings
make papers-db-up             # Start PostgreSQL
make papers-backup            # Start local PostgreSQL if needed, dump and check its papers DB
make papers-backups           # List completed archives in ~/rag-demo-backups
make papers-init-db           # Create catalogue tables, not paper records
make papers-backfill DAYS=7   # Save matching metadata and queue pending builds
make papers-status
make papers-process LIMIT=2   # Explicit PDF download + paid embedding/indexing step
make papers-status
make papers-audit             # Read-only SQL/Qdrant consistency report; no repair/model calls
make papers-count             # Count documents with an active ready build (arXiv + uploads)
```

For an upgrade, quiesce ingestion and use `make papers-backup`; finish old Redis batches with the
previous worker, stop API/worker/UI, run `papers-init-db`, then
`make papers-import-uploads LEGACY_MODEL=text-embedding-3-small` (confirm the actual old
embedding model). Adoption records observed legacy vectors in SQL without touching
Qdrant or re-embedding. Run the audit and recreate API/worker/UI to apply new environment
and artifact-volume settings. Full rollout instructions are in the catalogue guide.

Backup helpers use host Python 3 (`scripts/papers_backup.py`) and Compose PostgreSQL
tools, not app/model dependencies. Default directory is outside the repo; override with
`BACKUP_DIR=...`. `papers-backup-check FILE=...` decodes the archive without executing SQL.
New archives are private, uniquely named and only published after a successful check;
failed attempts retain `.partial` files. These commands target local `postgres/papers`,
not `PAPERS_DATABASE_URL`, Qdrant, artifacts or Airflow state. No live restore, scheduled
backups, retention deletion or off-site copying is implicit. Archive checks are not
full restore rehearsals. See `docs/operations/catalogue.md#backup-commands`.

`pending` means catalogued but not yet searchable; `ready` means processing/indexing
succeeded. Inspect current status instead of assuming that "fetched" means embedded
or repeating historical paper counts from this discussion. `papers-sync` is metadata
only; `papers-daily LIMIT=10` syncs and processes **once**, not a scheduler installation.
`DAYS`/`LIMIT` overrides are optional; otherwise CLI/.env defaults apply. Preview and
backfill also accept `UNTIL=YYYY-MM-DD`. Containerized CLI and scheduling instructions
are in `docs/getting-started/arxiv.md`; the README links the quick-start sequence.

### Streamlit corpus selection and troubleshooting

- **Document inventory** defaults to **All sources** and calls `GET /catalogue?source=all`.
  It shows registered totals, latest states and whether an active indexed build exists.
  Inventory source selection is independent of **Query source**. Upload acceptance is
  no longer displayed as completed ingestion. A failed replacement may retain an older
  ready build; latest-state counts and active-build counts can therefore overlap.
- `/documents` is a compatibility ready-upload listing backed by SQL; `/papers` lists
  active scoped arXiv builds. PostgreSQL/schema failure returns 503. The old ambiguous
  **Currently in database** button was removed. A 404 indicates stale/missing routes,
  not lost embeddings. Do not re-ingest papers to repair a listing.
- If a running bind-mounted API lacks a newly added route, `docker compose restart api`
  loads it; image-only deployments need a rebuild/redeploy. Refresh Streamlit and check
  the UI if you still see the old **Currently in database** button.
- Vanilla retrieves densely without reranking; Hybrid fuses dense and full-text-filtered
  dense candidates, then reranks. Both use the same active corpus and grounding prompt.
  The corpus fingerprint detects changes; it is not a historical snapshot store.
  Use **Start new conversation** after ingestion changes active papers; it clears chat
  and the corpus fingerprint. **Refresh document inventory** only updates the listing.
  Corpus/mode/model changes isolate chat context; form submission prevents sidebar
  changes from silently repeating model calls.

### Verification and remaining limits

Use `make test` and `make docs-build`. The unit suite includes offline ingestion,
activation/citation/mode regressions, corpus-listing HTTP tests with mocked clients,
schema migration, legacy adoption, equal-count/wrong-ID drift, sync/Batch failure paths,
a Streamlit all-source inventory test, and Make dry-run tests. Some HTTP tests run handlers
inline because sandbox worker threads can stall; do not equate mocked HTTP coverage
with a real deployment smoke test. Never run paid ingestion as an implicit test.

`make papers-audit` compares active manifests to Qdrant, reports unregistered points,
and distinguishes retained old builds from incomplete jobs. It never repairs/deletes
or calls models. Nonzero can mean drift, concurrent changes or an operational error;
rerun in a quiet window before repair. Legacy adoption establishes an observed baseline,
not proof of complete historical PDF extraction or the original embedding model.

Check live PostgreSQL readiness, `/catalogue`, `/papers` and the Qdrant collections separately
when debugging a deployment; `/health` currently checks Redis/Qdrant, not PostgreSQL.
The arXiv path is text-only: no OCR, automated figure enrichment, equation/table-aware
parsing or graph extraction. Existing uploaded-PDF figure processing remains separate.
Migration v1→v2 is implemented; a general migration framework, operator retry/reset,
ambiguous remote-Batch submission recovery, interrupted-upload recovery, stale-build cleanup and
historical snapshot serving remain follow-ups; see the guide for detailed limitations.

## Optional daily orchestration

- `src/api/papers/schedule.py` is scheduler-independent; `schedule_store.py` persists
  daily state in additive `paper_daily_runs` (created by `papers-init-db`; schema v2
  remains compatible). One immutable plan per actual UTC day, fixed build IDs and
  persisted per-build attempt reservations before paid work. No refilling on retries.
- `make papers-scheduled LIMIT=10` explicitly runs discovery/process/audit/report once;
  `make papers-run-status [RUN_DATE=YYYY-MM-DD]` only reads state. Legacy `papers-daily`
  and `papers-process` remain outside this scheduled budget. Do not run both schedulers.
- `dags/arxiv_daily.py` targets Airflow 3: 07:15 UTC, catchup false, one active run/task,
  paused on creation, one retry/task, two-hour task timeouts. Audit/report use all_done;
  report fails on unsuccessful upstream stages, so an audit cannot mask ingestion failure.
- `PAPERS_RUN_MAX_ATTEMPTS` defaults to two per selected build/day, also bounded by the
  lifetime build attempt budget. Interrupted attempts count. No exact dollar/token cap.
  Paid daily stages reject historical dates; retries crossing midnight fail for review.
- Monitoring is optional locally by explicit user choice: `PAPERS_REQUIRE_MONITORING`
  defaults false. Empty `PAPERS_ALERT_WEBHOOK_URL` / `PAPERS_HEARTBEAT_URL` log warnings
  and persist notification status `skipped`, never `sent`. Missing optional endpoints
  do not block successful ingestion/reporting; actual ingestion/audit failures still fail.
  Configured HTTPS endpoints are used (failure JSON POST / success GET); delivery errors
  still fail reporting. Set the strict flag true to require both URLs before processing.
  Without an external heartbeat monitor there are no missed-run/host-outage alerts.
  Notifications are at-least-once; URLs are secrets. Strict-mode errors name the required
  settings without exposing values. Rebuild/recreate Airflow to apply code/env changes.
- Optional Compose `airflow` profile uses a pinned Airflow image, an isolated app venv,
  and separate orchestration PostgreSQL. `make airflow-up` never unpauses a new DAG;
  restarting a previously enabled DAG preserves its enabled state. Do not enable live
  schedules, send test alerts or invoke paid ingestion implicitly as implementation tests.
- The standalone service is localhost-only development infrastructure, not production
  Airflow. Docs: `docs/operations/daily-ingestion.md`. Tests use offline DAG/API doubles;
  `make airflow-check` inspects actual import errors after building without running tasks.
