# Unified catalogue and index consistency

PostgreSQL now catalogues **both uploaded PDFs and arXiv papers**. The two Qdrant
collections remain separate; one catalogue does not require moving or re-embedding
their vectors. Streamlit's **Document inventory** defaults to **All sources** and is
independent of **Query source**, which still selects uploads or arXiv for answering.

## Upgrade an existing installation

Pause scheduled ingestion and new uploads, and let in-flight uploads finish before
upgrading. Use `make papers-backup` for the PostgreSQL backup. This release migrates schema version 1 to
2: `papers.arxiv_id` becomes `source_id`, and a `source` column distinguishes `arxiv`
from `uploads`. Existing paper/version/build IDs and manifests are preserved. The
old API/worker code must not keep running against the new schema.

**Legacy OpenAI batches:** if Redis still contains `pending_openai_batches`, finish
those jobs with the previous worker release before upgrading. The new poller does
not guess/adopt unfinished legacy jobs: it warns and leaves their Redis state intact.
Its normal jobs are now tracked durably in PostgreSQL, not expiring Redis metadata.

Once ingestion is quiescent:

```bash
make papers-backup
docker compose stop api ingestion-worker streamlit-app
make papers-db-up
make papers-init-db

# Confirm the actual model used by the old uploader. Its default was this model.
# Writes catalogue records only; does not change Qdrant or call a model API.
make papers-import-uploads LEGACY_MODEL=text-embedding-3-small

# Read-only verification; returns nonzero on inconsistencies.
make papers-audit

mkdir -p data/paper_artifacts temp_uploads
docker compose up -d --build api ingestion-worker streamlit-app
```

`papers-init-db` is idempotent and does not delete records. PostgreSQL now starts as
part of the normal Compose stack. Recreate the API and worker, not just restart them,
to apply the worker's PostgreSQL connection and artifact-volume settings. Host CLI
uses `localhost`; Compose containers use `postgres`. Keep both configurations pointed
at the same database, Qdrant endpoint, collections and embedding model.

Afterward, refresh Streamlit and use **Refresh document inventory** with **All sources**.
The existing thesis and active arXiv papers should appear together after successful
legacy import. No fixed document count is assumed: inspect your current inventory.
Inventory refresh preserves your chat. **Start new conversation** clears it and lets
your next question use the latest ready documents.

## Backup commands

```bash
make papers-backup                    # Create and check a timestamped backup
make papers-backups                   # List completed backups, newest first
make papers-backup-check FILE="/path/to/papers-....dump"  # Check again; no restore
```

Backups go to **`~/rag-demo-backups`**, outside the repo. To use another folder, add
`BACKUP_DIR="/your/backup/folder"` to the backup/list command. Only Python 3 and Docker
Compose are needed; no host PostgreSQL tools or app dependencies are required.

`papers-backup` starts/waits for the local Compose `postgres` service, dumps its
**`papers` database** as user `rag`, checks the full archive can be decoded, then
prints the filename. Files have owner-only permissions and unique UTC names. A failed
dump/check exits nonzero and leaves a `.partial` file, never a completed backup.

The check uses [pg_restore](https://www.postgresql.org/docs/16/app-pgrestore.html) to
generate SQL into `/dev/null`; it **does not execute SQL or restore a database**.
Archive readability is not a substitute for a restore rehearsal into a separate database.

These commands cover the **local paper catalogue only**, not a remote database selected
by `PAPERS_DATABASE_URL`, Airflow's database, Qdrant, or PDF/image files. No automatic
backup schedule, retention/deletion, or off-machine copy is installed. Keep an off-machine
copy for disaster recovery; keep sensitive archives out of Git. Existing backups are never overwritten.

## Existing-vector adoption is not re-ingestion

`papers-import-uploads` scans the configured upload collection and groups existing
points by content hash, falling back to filename/title for old payloads. It verifies
that vectors exist, records the point IDs as a baseline manifest, then activates the
document in SQL. Repeating the command skips already registered points. It does not
delete points, add payload tags or re-embed any text.

The baseline proves what is currently stored, **not** whether an old extraction
captured every page/figure. Existing vectors do not reliably identify the model that
created them, so the command requires explicit model confirmation. Uploads are
content-addressed: identical content is one document; changed bytes create another
document, even if the filename is unchanged. arXiv retains its own version numbering.

## Shared completion rules

| Latest build state | Meaning |
| --- | --- |
| `pending` | Registered; processing has not started |
| `running` | Extraction/indexing in progress |
| `waiting_batch` | Text indexed privately; waiting for all figure results |
| `ready` | Expected point IDs, valid vectors and document/version payload identity verified |
| `failed` | A processing stage failed; error class is recorded |

Both ingestion paths use the shared verifier in `src/api/papers/consistency.py`.
New uploads use deterministic, build-scoped point IDs. The expected point manifest
is persisted before upload indexing starts. Partial results never activate the
document. Sync figure/storage failures and missing/failed Batch results are no longer
silently treated as success. A failed replacement does not invalidate an earlier
active build. Inventory therefore shows the latest state **and** whether an active
indexed version remains available; these counts can overlap.

New upload batches persist batch ID, expected figure IDs and reconstruction payloads
in the build manifest. The poller activates only after all results are present and
the complete index verifies. A transient polling request failure can be retried on
the next cycle; a processing/terminal Batch failure marks the build failed for review.
Batch submission and SQL are not one distributed transaction: if a process dies
between remote submission and saving its batch ID, review the remote job before
retrying to avoid duplicate paid work. Interrupted `running` uploads also need operator
review; there is no automatic lease-expiry/recovery service in this release.

New upload PDFs, text/payloads, figure bytes and manifests use the artifact store;
figures also retain their existing local/Azure image-serving path. In ephemeral
deployments configure persistent storage for **both** artifacts and served figures.
`/ingest` means processing was accepted, not completed; refresh inventory for status.

Queries and metadata handlers use SQL-active builds. Unregistered legacy uploads are
intentionally excluded until adopted. `GET /documents` is now a compatibility listing
of ready uploads from SQL; `GET /papers` lists active scoped arXiv papers;
`GET /catalogue?source=all` reports all registered documents and processing states.
The inventory is catalogue state, **not** an on-demand Qdrant health check. Query
configuration/scope can further restrict which active builds are used.

## Read-only audit

```bash
make papers-audit
```

The audit checks active builds across both sources against Qdrant:

- Expected versus actual point IDs/counts, including equal-count substitutions.
- Missing/invalid vectors and incorrect document/version identity on new builds.
- Unregistered points, including uploads that have not yet been adopted.
- Retained old builds and incomplete jobs, reported separately rather than deleted.

Old arXiv manifests derive deterministic expected IDs from their saved chunk counts.
Adopted legacy uploads use their observed baseline and original hash/filename filter.
The audit never calls an embedding model, writes a status, repairs data or deletes
vectors. It downloads stored vectors to validate presence/finite values, so large
collections can incur read latency/egress. It does not prove semantic embedding
correctness or check every stored artifact's availability/checksum.

Exit code 0 means the inspected active builds matched and no unregistered points were
found. Nonzero means drift, a concurrent catalogue change or an operational failure;
inspect the report/error before acting. This is not a distributed snapshot: rerun in
a quiet ingestion window if results are inconclusive. No periodic audit is installed.

For missing points, first check endpoint/collection configuration and service health.
For legacy unregistered points, use the explicit adoption command after review.
Never delete retained or incomplete builds just because they are not active. General
repair, retry/reset, garbage collection and restore tooling remain separate follow-ups.

## Verification

`make test` covers migration/idempotence, mixed-source inventory, legacy adoption,
read-only audit, same-count drift, sync/batch failure handling and retained versions.
The Streamlit test verifies that an upload-selected query can still display both
uploads and arXiv in the all-source inventory without making model calls. Service
clients are mocked or use local test stores; production PostgreSQL/Qdrant/Blob and
paid-model ingestion still require a deployment smoke test.
