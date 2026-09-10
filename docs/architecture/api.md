# API Surface

The FastAPI application is served on port 8000. Interactive documentation is available at
<http://localhost:8000/docs> whenever the backend is running.

## Endpoints

| Method | Path | Tag | Purpose |
| --- | --- | --- | --- |
| `GET` | `/` | — | Welcome message |
| `GET` | `/health` | `system` | Liveness probe, used by the Compose healthcheck |
| `GET` | `/documents` | `system` | List uploaded PDFs from the legacy Qdrant collection |
| `GET` | `/papers` | `papers` | List ready arXiv papers and the current corpus fingerprint |
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

Streamlit's **Currently in database** button follows the **Corpus** selection:
**Uploaded PDFs** calls `GET /documents`; **arXiv star clusters** calls `GET /papers`.
Both return `titles` and `total_documents`. `/documents` paginates through the upload
collection and groups chunks/figures by file hash (falling back to filename/title
for older payloads). A missing upload collection returns an empty list; connectivity
failures return HTTP 503. `/papers` lists only SQL-active, ready builds—not pending
metadata discoveries. The two listings intentionally remain separate.

If `/documents` returns HTTP 404, the running backend is missing this route. Restart
the API after updating its code (rebuild the image if code is not bind-mounted).

## Middleware

`RequestIDMiddleware` attaches a correlation ID to every request so logs across the API and
the worker can be tied together. CORS is fully permissive by default and is controlled by
`ALLOW_ORIGINS`.

## Lifecycle

An `asynccontextmanager` lifespan handler logs startup and shutdown and closes the shared
`httpx.AsyncClient` (built with `settings.DEFAULT_TIMEOUT`) on the way out.
