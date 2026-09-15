# API Surface

The FastAPI application is served on port 8000. Interactive documentation is available at
<http://localhost:8000/docs> whenever the backend is running.

## Endpoints

| Method | Path | Tag | Purpose |
| --- | --- | --- | --- |
| `GET` | `/` | — | Welcome message |
| `GET` | `/health` | `system` | Liveness probe, used by the Compose healthcheck |
| `GET` | `/documents` | `system` | List ready uploads from the shared SQL catalogue |
| `GET` | `/papers` | `papers` | List ready arXiv papers and the current corpus fingerprint |
| `GET` | `/catalogue?source=all` | `papers` | Unified inventory with processing states; source may be all, uploads or arxiv |
| `POST` | `/rag2` | `rag` | Ask a question and get a cited answer |
| `GET` | `/images/{image_name}` | `rag` | Serve a figure referenced by an answer |
| `POST` | `/ingest` | `ingestion` | Ingest PDF documents with smart batching |

Static figure files are additionally mounted at `/api/images`, backed by
`/app/src/api/data/images` inside the container.

## `POST /rag2`

The main entry point. It resolves the session's memory, runs the
[RAG pipeline](rag-pipeline.md), and returns the answer together with deduplicated sources
and any cited figures. Supporting helpers in `rag_router.py`:

- `chat_memory(session_id)` — renders the stored history into prompt-ready text.
- `answer_from_chat_context(question, chat_history, model)` — answers directly from
  conversation context when retrieval is unnecessary.
- `format_answer_for_display(ans)` — formats the structured answer for the UI.
- `_process_images(raw_images, request)` — rewrites image paths into absolute URLs.

## `POST /ingest`

Accepts uploaded PDFs and hands them to `start_smart_ingestion`, which chooses between
real-time and OpenAI Batch processing. See [Ingestion](ingestion.md).

## Corpus listings

Streamlit's **Refresh document inventory** button calls `GET /catalogue`, defaulting
to **All sources** independently of **Query source**. It returns total registered
documents, active indexed documents, latest-state counts, and per-document source,
state, active version and collection. A failed replacement can coexist with an older
active version. `/documents` remains a ready-upload compatibility listing and `/papers`
remains a scoped ready-arXiv listing; both now use PostgreSQL. Catalogue/schema failures
return HTTP 503. These endpoints do not themselves verify live vectors: use
`make papers-audit`. See [Catalogue and consistency](../operations/catalogue.md).

If `/documents` returns HTTP 404, the running backend is missing this route. Restart
the API after updating its code (rebuild the image if code is not bind-mounted).

## Middleware

`RequestIDMiddleware` attaches a correlation ID to every request so logs across the API and
the worker can be tied together. CORS is fully permissive by default and is controlled by
`ALLOW_ORIGINS`.

## Lifecycle

An `asynccontextmanager` lifespan handler logs startup and shutdown and closes the shared
`httpx.AsyncClient` (built with `settings.DEFAULT_TIMEOUT`) on the way out.
