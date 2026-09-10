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
  and figure descriptions become Qdrant points. Small uploads run synchronously; uploads of
  `INGESTION_BATCH_THRESHOLD` files or more submit figure analysis to OpenAI Batch. The poller
  (`src/api/ingestion/poller.py`) finishes those jobs from Redis metadata.
- **Storage:** local figures live under `src/api/data/images`; Azure Blob storage is selectable
  with `STORAGE_MODE=AZURE`. Local image URLs use `EXTERNAL_API_URL`.
- **Deployment:** `docker-compose.yml` runs UI, API, ingestion worker, and Redis. Qdrant is
  normally external (Cloud); the local Compose service is intentionally commented out.
  PostgreSQL and the one-shot arXiv CLI are opt-in services under the `papers` profile.

## Configuration and decisions

- `src/api/core/config.py` (`Config`) configures the existing API/RAG/upload stack;
  `src/api/papers/settings.py` (`PaperSettings`) configures the arXiv catalogue/CLI. Secrets and
  endpoints come from `.env`/environment; defaults in that class are intentional current
  defaults. Prompt templates are YAML files under `src/api/rag/prompts/`.
- `config.yaml` is currently **not loaded by `Config`**. Treat it as legacy/experimental until
  the code is changed to consume it; do not assume its collection or model settings are active.
- Generation provider is inferred from the model name (`gpt-*`/`o1-*` => OpenAI; Groq for
  `openai/gpt-oss-*` and other names), not from `GENERATION_MODEL_PROVIDER`.
- The uploaded-PDF ingestion implementation is `ingest_documents.py` plus `worker.py` and
  `poller.py`. `ingest_documents_old.py`, `ingest_documents_now.py`, `src/api/utils.py`,
  `evals/old/`, notebooks, and `docling_trial/` are experiments/legacy references.
- Preserve both corpora: arXiv uses `PAPERS_COLLECTION`, distinct from the uploaded-PDF
  `QDRANT_COLLECTION_NAME`. Ingestion may create collections, not a Qdrant Cloud cluster;
  the managed cluster must be provisioned separately.

## Important current caveats

- `retrieval.py` uses the configured Redis host/port/database for local and Compose runs.
- The Batch poller does not yet write the same figure payload schema as synchronous ingestion
  (`page` vs `page_number`, and caption/year omissions). Batch-ingested figure citations can
  therefore lack page/caption metadata.
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
make ingest        # standalone ingestion_batch script
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

`src/api/papers/` adds a separate PostgreSQL catalogue, versioned artifacts and a
text-only arXiv processing CLI. Default scope: `astro-ph.GA` AND star-cluster phrases
in titles/abstracts. See `docs/getting-started/arxiv.md` for commands and limitations.
Metadata settings are isolated in `PaperSettings` so discovery needs no model keys.
Use `python -m src.api.papers scope`, `init-db`, `backfill`, `sync`, `process`, `daily`,
or `status`. Nothing schedules paid ingestion automatically. PostgreSQL and the CLI
are in the Compose `papers` profile; existing uploads use the legacy collection.

Explicit `/rag2` modes `vanilla`/`hybrid` bypass intent routing. `corpus=arxiv` filters
Qdrant to SQL-active builds and supports a corpus-change fingerprint. Streamlit
exposes these presets with isolated chat context. Neither preset is agentic/graph RAG.
Hybrid is dense + full-text-constrained dense RRF with Cohere rerank, not sparse BM25.
Tests: `uv run --group dev pytest tests/unit -q` (offline, no paid calls).

### Storage and activation guarantees

- PostgreSQL is the catalogue/source of truth: `papers`, `paper_versions`,
  `paper_builds` (also the processing queue), and `paper_checkpoints`. Canonical paper,
  arXiv version and processing build IDs are distinct. Abstracts are source metadata,
  not generated summaries.
- Build manifests record processing/model identity, artifact hashes/locations and
  verified chunk counts. Only successful builds become active; failed replacements
  leave the previous active version queryable. Qdrant queries filter to SQL-active
  builds; old points are retained, not automatically deleted.
- `backfill` uses bounded submission-date Search API queries; `sync` uses incremental
  OAI-PMH metadata updates with pagination/checkpoints and overlap. Discovery queues
  work independently of PDF limits, preserving the backlog. Writes are serialized by
  a PostgreSQL advisory lock; retries are bounded by `ARXIV_MAX_ATTEMPTS`.
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
make papers-db-up             # Start the opt-in PostgreSQL service
make papers-init-db           # Create catalogue tables, not paper records
make papers-backfill DAYS=7   # Save matching metadata and queue pending builds
make papers-status
make papers-process LIMIT=2   # Explicit PDF download + paid embedding/indexing step
make papers-status
```

`pending` means catalogued but not yet searchable; `ready` means processing/indexing
succeeded. Inspect current status instead of assuming that "fetched" means embedded
or repeating historical paper counts from this discussion. `papers-sync` is metadata
only; `papers-daily LIMIT=10` syncs and processes **once**, not a scheduler installation.
`DAYS`/`LIMIT` overrides are optional; otherwise CLI/.env defaults apply. Preview and
backfill also accept `UNTIL=YYYY-MM-DD`. Containerized CLI and scheduling instructions
are in `docs/getting-started/arxiv.md`; the README links the quick-start sequence.

### Streamlit corpus selection and troubleshooting

- **Currently in database** follows **Corpus**: Uploaded PDFs calls `GET /documents`
  (`system_router.py`); arXiv star clusters calls `GET /papers` (`papers_router.py`).
  Both return `titles` and `total_documents`; `/papers` lists only ready, active papers.
- `/documents` paginates Qdrant and groups chunks/figures by file hash, with legacy
  filename/title fallbacks. Missing collection: empty listing; unavailable Qdrant: 503.
  This route was added after a reported 404. A 404 is a route/deployment problem, not
  evidence that embeddings are missing. Do not re-ingest papers to repair a listing.
- If a running bind-mounted API lacks a newly added route, `docker compose restart api`
  loads it; image-only deployments need a rebuild/redeploy. Refresh Streamlit and check
  corpus selection if an arXiv listing unexpectedly calls `/documents`.
- Vanilla retrieves densely without reranking; Hybrid fuses dense and full-text-filtered
  dense candidates, then reranks. Both use the same active corpus and grounding prompt.
  The arXiv fingerprint detects corpus changes; it is not a historical snapshot store.
  Use **Refresh arXiv corpus / reset comparison** after ingestion changes active papers.
  Corpus/mode/model changes isolate chat context; form submission prevents sidebar
  changes from silently repeating model calls.

### Verification and remaining limits

Use `make test` and `make docs-build`. The unit suite includes offline ingestion,
activation/citation/mode regressions, corpus-listing HTTP tests with mocked clients,
and Make dry-run tests that do not execute ingestion. Some HTTP tests run handlers
inline because sandbox worker threads can stall; do not equate mocked HTTP coverage
with a real deployment smoke test. Never run paid ingestion as an implicit test.

Check live PostgreSQL readiness, `/papers` and the selected Qdrant collection separately
when debugging a deployment; `/health` currently checks Redis/Qdrant, not PostgreSQL.
The arXiv path is text-only: no OCR, automated figure enrichment, equation/table-aware
parsing or graph extraction. Existing uploaded-PDF figure processing remains separate.
General schema migrations, operator retry/reset tooling, stale-build cleanup and
historical snapshot serving remain follow-ups; see the guide for detailed limitations.
