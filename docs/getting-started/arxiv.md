# arXiv star-cluster milestone

arXiv discovery is opt-in. PostgreSQL now catalogues both arXiv papers and manually
uploaded PDFs, with versioned artifacts, bounded processing and a Vanilla/Hybrid
query-time switch. Existing uploads retain their Qdrant collection. No knowledge
graph or autonomous agent is added. Existing installations must follow the
[catalogue upgrade and consistency guide](../operations/catalogue.md) first.

## Scientific scope

The initial scope is **star-cluster papers within `astro-ph.GA`** (Astrophysics of
Galaxies). arXiv explicitly includes star clusters in this category; there is no
separate star-cluster category. `astro-ph.SR` (Solar and Stellar Astrophysics) is an
optional future expansion, not part of this initial corpus. Galaxy clusters are
not the same objects as star clusters.

```dotenv
ARXIV_CATEGORIES=astro-ph.GA
ARXIV_TOPIC_TERMS=star cluster,stellar cluster,globular cluster,open cluster,young massive cluster,nuclear star cluster
```

Selection requires a matching category **AND** at least one configured phrase in
the title or abstract. Cross-listed categories count, not just the primary category.
Matching ignores case, punctuation/hyphens and accepts simple plural forms. Duplicate
cross-list records share one arXiv identity. Empty `ARXIV_TOPIC_TERMS` selects the
whole category. Phrases are deterministic filters, not an LLM scientific classifier:
papers mentioning only a cluster name (e.g. NGC 104) can be missed. Review the first
sample and adjust terms before extending the backfill.

See arXiv's [category taxonomy](https://arxiv.org/category_taxonomy) and
[Search API manual](https://info.arxiv.org/help/api/user-manual.html).

## Architecture and invariants

| Component | Responsibility |
| --- | --- |
| PostgreSQL | Canonical paper IDs, version metadata, build/job states, discovery checkpoints, active version |
| Qdrant (`PAPERS_COLLECTION`) | Rebuildable chunk embeddings and citation/filter payloads |
| Local directory / private Azure Blob container | Content-addressed PDF, source metadata, chunks and build manifest |
| Redis | Existing conversation memory, isolated by corpus/mode/model/fingerprint |

Paper UUIDs derive from unversioned arXiv IDs; version IDs and build IDs are separate.
An arXiv abstract is stored as source metadata, not relabelled as a generated summary.
Each build records the embedding model, processing-pipeline fingerprint, content
hashes, artifact locations and verified chunk count. A new version becomes active
only after artifacts and Qdrant writes succeed. Old points are retained but excluded
by the SQL-derived ready-build filter. No distributed transaction is assumed.

Commands serialize through a PostgreSQL advisory lock. Pending/failed/interrupted
builds are retried with deterministic IDs, up to `ARXIV_MAX_ATTEMPTS`. Daily PDF limits
do not truncate metadata discovery: unprocessed work stays in PostgreSQL. Failures
are visible with `status`; processing exits nonzero if any attempted paper fails.
For now errors expose exception classes only (not credentials or raw HTTP details).

`backfill` uses a bounded **submission-date** Search API query. `sync` uses incremental
[OAI-PMH metadata updates](https://info.arxiv.org/help/oa/index.html), resolves matching
records through the Search API to obtain exact current version numbers, and queues
new builds. OAI dates are metadata-change dates, not submission dates. Pagination must
complete before a checkpoint advances; the first response timestamp and a one-day
overlap make interrupted harvests replay-safe. OAI deletion headers hide affected
papers without destroying their artifacts. Changing topic scope creates new discovery
checkpoints; run another backfill to populate older papers in the new scope.

Requests are serial and spaced by at least 3.1 seconds, with bounded metadata retries
and `Retry-After` handling. Run only **one** scheduler across your deployments, even
if they have different databases: arXiv's limits apply collectively across the legacy
API endpoints and machines. Configure an identifiable `ARXIV_USER_AGENT` with contact
information. See [arXiv API terms](https://info.arxiv.org/help/api/tou.html).

## Local quick start

### Upgrade existing PDFs to Markdown extraction

Both arXiv and GUI uploads now use **PyMuPDF4LLM → per-page Markdown →
structure-aware chunks**. Chunking preserves section breadcrumbs and PDF page numbers,
uses a 512-token cap with up to 64 tokens of paragraph overlap, and splits large tables
by complete rows with repeated headers. OCR is disabled. Oversized table rows fail for
review rather than being silently truncated. This improves reading order, but does not
guarantee correct equations, tables or scientific meaning.

New builds save `document.md`, `pages.json`, `chunks.json` and extraction settings as
content-addressed artifacts. Existing PDFs/vectors are **not upgraded automatically**.
Changing extraction changes the build fingerprint, not the paper's identity.

For an existing installation, pause the Airflow DAG and let running ingestion/figure
batches finish before rebuilding workers. Do not run old and new ingestion workers
against the same catalogue during the upgrade.

```bash
make airflow-stop
make papers-backup
uv sync --group dev --group frontend
make papers-extractor-setup       # Cache public tokenizer vocabulary; no model calls
docker compose up -d --build api ingestion-worker streamlit-app
make papers-reindex-preview       # Read-only list of active arXiv papers needing upgrade
make papers-reindex LIMIT=2       # Pilot: download exact PDF versions + paid embeddings
make papers-audit
make papers-reindex LIMIT=50      # After inspecting pilot quality: upgrade up to 50 remaining
make papers-audit
make papers-reindex-preview       # Check remaining/blocked replacements
```

Run commands separately and stop on failure. `papers-reindex` targets **existing active
arXiv papers in the configured scope/collection/model**, not unrelated discovery backlog.
Each old build remains searchable until its replacement passes vector/identity checks.
Re-running skips current-pipeline active papers and resumes failed replacements within
the attempt budget; it does not delete old points or bypass exhausted attempts. Interrupted
embedding calls may still incur charges. `LIMIT` defaults to `ARXIV_DAILY_LIMIT`.
This manual command is separate from Airflow's daily budget.

`papers-count` includes uploads, so 50 total documents need not mean 50 arXiv upgrades.
For existing **GUI uploads**, re-upload the same PDF bytes after rebuilding the API.
Old-extractor builds now produce a replacement under the same content identity; already
current builds are skipped. Upload replacement also reruns metadata/summary/figure work
and may incur those costs. Legacy-adopted documents without a matching SHA-256 content
identity may need operator review; do not assume a filename proves identical content.

To inspect extraction locally before any embeddings:

```bash
make papers-extract-preview PDF="/path/to/paper.pdf" EXTRACT_DIR=data/extraction-pilot
```

This saves Markdown/pages/chunks under the new inspection directory, never overwrites
an existing directory, and does not access databases or call a model. The tokenizer
cache must be prepared first for offline use. Containers bundle that cache at build time.

After verifying the upgraded corpus, use `make airflow-up` / `make airflow-check` to
rebuild Airflow too, then explicitly unpause the DAG when ready. Existing daily run plans
are immutable: a plan created under the old pipeline cannot be retried under the new one;
use the next day's scheduled run or the manual re-index workflow.
Create a **new evaluation preview directory** after re-indexing; old snapshots still
contain the old extracted text. Retain them for comparison rather than editing hashes.

### Fresh installation

Merge the new settings from `.env.sample` into your existing `.env`; do **not**
overwrite your API keys. Default PostgreSQL credentials are for local development
only. Qdrant Cloud must already exist; these commands create a **collection**, not a
Cloud cluster. `PAPERS_COLLECTION` must differ from `QDRANT_COLLECTION_NAME`.

```bash
uv sync --group dev --group frontend
uv run python -m src.api.papers scope

# Metadata preview only: no DB writes, PDF downloads or embedding charges.
uv run python -m src.api.papers backfill --days 7 --dry-run

# PostgreSQL only; persistent named volume, localhost-only published port.
docker compose --profile papers up -d postgres
uv run python -m src.api.papers init-db

# Persist matching metadata and queue work, then process at most two PDFs.
uv run python -m src.api.papers backfill --days 7
uv run python -m src.api.papers process --limit 2
uv run python -m src.api.papers status
```

`process` incurs embedding API usage. Size, chunk-count, attempt and paper-count
limits bound work, but are not a dollar budget. Backfill refuses category windows
with more than 1,000 records; use shorter windows and `--until YYYY-MM-DD` for older
intervals. arXiv APIs do not require a personal API key.

### Make shortcuts

Run `make papers-help` for the command summary. These targets wrap the host-side
commands above; they do not run the Python CLI inside a container. PostgreSQL itself
runs in the separate Compose `postgres` service, now part of the normal stack.

| Command | Effect | Embedding API usage |
| --- | --- | --- |
| `make papers-scope` | Print configured categories and topic phrases | No |
| `make papers-preview DAYS=7` | Fetch and print matching metadata; no DB connection or writes | No |
| `make papers-db-up` | Start PostgreSQL and wait for its health check | No |
| `make papers-init-db` | Create catalogue tables in the configured database | No |
| `make papers-backfill DAYS=7` | Save matching metadata and queue processing | No |
| `make papers-status` | Inspect processing states | No |
| `make papers-count` | Count documents with an active ready build, across arXiv and uploads | No |
| `make papers-audit` | Read-only SQL/Qdrant consistency check | No |
| `make papers-import-uploads LEGACY_MODEL=text-embedding-3-small` | Register existing upload vectors; confirm their original model first | No |
| `make papers-process LIMIT=2` | Download/index up to two pending PDFs | Yes |
| `make papers-sync` | Discover metadata changes and queue work | No |
| `make papers-daily LIMIT=10` | Run metadata sync and process up to ten PDFs, once | Yes |

For the first run, use preview → database start → table initialization → backfill →
status → processing → status. After backfill, matching records are `pending`, not
yet searchable; successful processing makes them `ready` for the arXiv corpus in
Streamlit. If no metadata matches, there is nothing to queue.

`DAYS` and `LIMIT` are optional overrides. When omitted, the CLI uses
`ARXIV_BACKFILL_DAYS` and `ARXIV_DAILY_LIMIT` from configuration. Preview and backfill
also accept an end date, for example:

```bash
make papers-preview DAYS=3 UNTIL=2026-09-01
```

Only `papers-db-up` starts a container. Other targets use the configured
`PAPERS_DATABASE_URL` and do not start PostgreSQL implicitly. From the host, use
`localhost:5432`; from Compose containers, the hostname is `postgres`. Database
`papers` persists in the Docker named volume `papers_postgres` across container
restarts/recreation. These targets do not remove volumes, overwrite `.env`, or
install a daily schedule. Keep cost-bearing processing as a separate, explicit step.

### Containerized CLI alternative

For containerized processing, create the bind mount as your host user before using
the non-root CLI container:

```bash
mkdir -p data/paper_artifacts
docker compose --profile papers build papers-cli api streamlit-app
docker compose --profile papers run --rm papers-cli init-db
docker compose --profile papers run --rm papers-cli backfill --days 7
docker compose --profile papers run --rm papers-cli process --limit 2
docker compose --profile papers up -d api streamlit-app
```

Set `LOCAL_UID`/`LOCAL_GID` when they differ from 1000. For host commands, use a
localhost `PAPERS_DATABASE_URL`; Compose uses the `postgres` service hostname.
If changing the local DB password, update both `PAPERS_DB_PASSWORD` and the host URL
(URL-encode reserved password characters). Changing the environment password does not
change a password inside an already-initialized PostgreSQL volume.

## Repeatable daily ingestion

`sync` discovers and queues metadata only; `process` drains pending work; `daily`
runs both with `ARXIV_DAILY_LIMIT`. Run a small backfill before enabling a schedule.

```bash
uv run python -m src.api.papers daily --limit 10
```

Alternatively, run `make papers-daily LIMIT=10` for the same one-shot operation.

For automation, prefer the [durable daily runner and optional Airflow DAG](../operations/daily-ingestion.md).
It freezes the day's paper selection, audits afterward and sends monitoring signals.
The DAG starts paused; monitoring is optional locally. Set `PAPERS_REQUIRE_MONITORING=true`
and configure both endpoints when external alerts are required.

The same durable runner can instead be scheduled with cron or an Azure Container Apps
Job. For example (replace paths; **do not also enable Airflow**):

```cron
15 7 * * * cd /absolute/path/rag-demo && /absolute/path/to/uv run python -m src.api.papers.schedule all --limit 10 >> /absolute/path/arxiv-daily.log 2>&1
```

The schedule uses the host timezone. No cron entry, cloud job, download or paid API
call is installed/executed just by starting the app. Monitor nonzero exit codes and
`status`. After three failed attempts, investigate before resetting attempts or
creating a new processing build; an operator retry/reset command is a follow-up.

## Query-time comparison

Open Streamlit, select **arXiv star clusters** under **Query source**, then **Vanilla**
or **Hybrid**. **Document inventory** independently defaults to **All sources**;
refresh it to see uploads and arXiv together, including pending/failed builds.

- Vanilla: dense retrieval, five chunks, no reranker.
- Hybrid: dense candidates plus full-text-constrained dense candidates, reciprocal
  rank fusion, then Cohere reranking to five chunks. This is not a BM25 sparse index.
- Both use the same embedding/generation settings, grounding prompt, citation schema
  and active-build filter. Explicit presets bypass intent routing. API clients that
  omit `mode` and select uploads retain the existing routed behavior.

The first query pins a corpus fingerprint in the GUI. If ingestion changes the
active builds, subsequent comparisons return a refresh warning instead of silently
comparing different corpora. **Start new conversation** clears chat and the fingerprint
so the next question uses the latest active corpus. **Refresh document inventory**
only updates the listing, preserving the conversation. This is a change detector,
not an archival snapshot/query-history system.
Changing mode/model/corpus clears chat context; changing a sidebar setting does not
resubmit a question. For a fair initial comparison, submit the same standalone
question with the same generation model in both modes. Uploaded PDFs must be registered
in the catalogue and now use active-build filtering/fingerprints too.

`GET /papers` lists ready papers and the current fingerprint. Example request:

```json
{"query": "Compare age estimation methods across these papers.", "mode": "vanilla", "corpus": "arxiv"}
```

Send it to `POST /rag2`. Include the returned `corpus_snapshot` on subsequent requests
to reject corpus changes. Returned sources include stable paper ID, arXiv ID, version,
page and original source URL. Retrieval can cite multiple papers already; balanced
per-paper evidence collection and systematic literature synthesis are later steps.

## Deployment and limits

Use managed PostgreSQL, your managed Qdrant cluster and a private Azure Blob container.
For ephemeral containers set `PAPERS_STORAGE_MODE=AZURE`, `PAPERS_AZURE_CONTAINER` and
`AZURE_STORAGE_CONNECTION_STRING` through deployment secrets. Provision the container
beforehand. This artifact configuration is separate from the legacy figure-storage
settings. Run `init-db` as an explicit release step and use the backend image with
command `python -m src.api.papers.schedule all` in your scheduled job, with the monitoring
settings from the [daily ingestion guide](../operations/daily-ingestion.md). The local Compose
PostgreSQL service is not a production deployment template.

The arXiv extractor does not perform OCR, figure description, semantic equation parsing,
references/entity extraction or graph building. Markdown table reconstruction is supported,
but complex tables and mathematical glyphs still need quality review.
Scanned PDFs fail explicitly. Metadata-only corrections are refreshed in the catalogue;
already-ready build metadata/embeddings remain the indexed revision until rebuilt.
No automatic stale-build garbage collection, general schema migration framework,
historical snapshot serving or UI ingestion dashboard is included yet. Back up the
catalogue and artifacts. Keep source/license metadata; do not assume all arXiv PDFs
can be publicly redistributed under the same terms.

## Offline verification

```bash
uv run --group dev pytest tests/unit -q
uv run --group dev mkdocs build
```

The new tests use fixture HTTP responses, temporary artifacts, SQLite for catalogue
logic and in-memory Qdrant. They do not contact arXiv, PostgreSQL, Azure or model APIs.
The existing `tests/integration/test_poller_logic.py` is a manual legacy Redis script,
not this suite. A real PostgreSQL/Cloud/Blob end-to-end smoke test remains a separate
deployment check before enabling the daily schedule.
