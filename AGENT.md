# RAG Demo — project handoff

## Purpose and current shape

This is a PDF-focused RAG demo: Streamlit (`src/chatbot_ui`) calls a FastAPI backend
(`src/api`), which retrieves from Qdrant and generates answers with OpenAI or Groq.
It supports source citations, figure retrieval, Redis-backed conversation memory, and
two ingestion modes. MkDocs documentation is in `docs/`; start at
`docs/architecture/index.md` for the fuller diagrams.

## Runtime architecture

- **UI:** `src/chatbot_ui/main.py`; sends `POST /rag2` and `POST /ingest` to `API_URL`.
- **API:** `src/api/main.py`; routers are in `src/api/api/`. `POST /rag2` classifies a
  question first, handles catalogue-style metadata questions directly, otherwise runs RAG.
- **RAG:** `src/api/rag/retrieval.py`: OpenAI embedding -> Qdrant RRF fusion of dense and
  full-text retrieval -> Cohere rerank -> structured OpenAI/Groq response. The model selects
  cited chunk IDs; only those sources/figures are returned.
- **Memory:** pickled `ConversationMemory` objects in Redis, per `session_id`, 10-message
  recent window plus a Groq summary; TTL is refreshed to one hour on every message.
- **Ingestion:** PDF text/figures are extracted with PyMuPDF. Text chunks, a document summary,
  and figure descriptions become Qdrant points. Small uploads run synchronously; uploads of
  `INGESTION_BATCH_THRESHOLD` files or more submit figure analysis to OpenAI Batch. The poller
  (`src/api/ingestion/poller.py`) finishes those jobs from Redis metadata.
- **Storage:** local figures live under `src/api/data/images`; Azure Blob storage is selectable
  with `STORAGE_MODE=AZURE`. Local image URLs use `EXTERNAL_API_URL`.
- **Deployment:** `docker-compose.yml` runs UI, API, ingestion worker, and Redis. Qdrant is
  normally external (Cloud); the local Compose service is intentionally commented out.

## Configuration and decisions

- `src/api/core/config.py` (`Config`) is the runtime configuration authority. Secrets and
  endpoints come from `.env`/environment; defaults in that class are intentional current
  defaults. Prompt templates are YAML files under `src/api/rag/prompts/`.
- `config.yaml` is currently **not loaded by `Config`**. Treat it as legacy/experimental until
  the code is changed to consume it; do not assume its collection or model settings are active.
- Generation provider is inferred from the model name (`gpt-*`/`o1-*` => OpenAI; Groq for
  `openai/gpt-oss-*` and other names), not from `GENERATION_MODEL_PROVIDER`.
- The current ingestion implementation is `ingest_documents.py` plus `worker.py` and
  `poller.py`. `ingest_documents_old.py`, `ingest_documents_now.py`, `src/api/utils.py`,
  `evals/old/`, notebooks, and `docling_trial/` are experiments/legacy references.

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

## Opt-in arXiv milestone

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
