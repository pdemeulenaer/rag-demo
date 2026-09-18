# Configuration

Runtime configuration comes from `.env` or process environment variables, loaded by the
Pydantic settings classes.

## Environment variables

Copy `.env.sample` to `.env` and populate it:

| Variable | Purpose |
| --- | --- |
| `GROQ_API_KEY` | Groq API key, used for generation and summarization |
| `QDRANT_API_KEY` | Qdrant Cloud API key |
| `QDRANT_URL` | Qdrant Cloud instance URL |
| `QDRANT_COLLECTION_NAME` | Uploaded-PDF collection holding dense and named BM25 sparse vectors |
| `EMBEDDING_API_URL` | Endpoint of the embedding model API |
| `EMBEDDING_MODEL` | Embedding model name, e.g. `text-embedding-3-small` |
| `EMBEDDING_MODEL_PROVIDER` | Embedding provider, e.g. `openai` |
| `GENERATION_MODEL` | Generation model name, e.g. `gpt-4.1` |
| `GENERATION_MODEL_PROVIDER` | Generation provider, e.g. `openai` |
| `AGENT_MODEL` | OpenAI model used for Agentic planning/sufficiency; final answers use `GENERATION_MODEL` |
| `AGENT_REASONING_EFFORT` | Reasoning effort for supported Agentic planner models (`minimal` by default) |
| `AGENT_MAX_COMPLETION_TOKENS` | Per-call Agentic planner output limit |
| `AGENT_MAX_ROUNDS` | Retrieval-round limit; application maximum is three |
| `AGENT_MAX_TOOL_CALLS` | Total read-only tool-call limit per request |
| `AGENT_MAX_EVIDENCE_CHUNKS` | Maximum distinct chunks accumulated by the agent |
| `AGENT_MAX_ELAPSED_SECONDS` | Agentic retrieval wall-time budget |
| `AGENT_MAX_PLANNER_TOKENS` | Combined planner/sufficiency token budget |
| `COHERE_API_KEY` | Cohere API key, used only by `hybrid_rerank` |
| `PAPERS_COLLECTION` | Separate arXiv dense+BM25 collection (`arxiv_papers_v2` by default) |
| `OPENAI_API_KEY` | OpenAI API key |
| `LANGFUSE_ENABLED` | Enable API traces and evaluation experiments |
| `LANGFUSE_PUBLIC_KEY` | Langfuse project public key |
| `LANGFUSE_SECRET_KEY` | Langfuse project secret key |
| `LANGFUSE_BASE_URL` | Host URL for this repo's Langfuse container (`http://localhost:3000`) |
| `LANGFUSE_BASE_URL_CONTAINER` | Internal Compose URL (`http://langfuse-web:3000`) |
| `LANGFUSE_ENVIRONMENT` | Environment label such as `local` or `staging` |
| `LANGFUSE_RELEASE` | Optional deployed application version |
| `LANGFUSE_DATASET_PREFIX` | Prefix for content-addressed evaluation datasets |

Langfuse is the only supported tracing and evaluation-experiment backend. See
[Observability](../operations/observability.md) for its repo-owned Docker stack and setup.

!!! danger "Never commit `.env`"
    `.env` is gitignored. On Azure, inject the same values through
    **App Service → Configuration** rather than baking them into an image.

Docker Compose adds two more at runtime: `REDIS_HOST` and `REDIS_PORT` point the backend
and the ingestion worker at the `redis` service, and the frontend gets `API_URL=http://api:8000`.

Dense-only collections cannot be upgraded in place. When adopting the current sparse index,
choose new `QDRANT_COLLECTION_NAME` and `PAPERS_COLLECTION` values, then follow the
[arXiv re-index procedure](arxiv.md#upgrade-existing-pdfs-to-the-current-retrieval-index).
The application creates collections, not the managed Qdrant Cloud cluster itself.

## Legacy `config.yaml`

`config.yaml` remains from an earlier implementation, but the active `Config` class does
**not** load it. Do not expect changes there to affect the API. Active model names and
prompt paths come from `src/api/core/config.py` defaults overridden by `.env`; prompt text
lives in YAML files under `src/api/rag/prompts/`.

The legacy file currently contains values such as:

```yaml
collection: 'test_collection_oai_test'

groq:
  summarization_model: 'llama-3.3-70b-versatile'
  summarization_prompt: 'Summarize the following text: {{text}}'
  temperature: 0.3
  max_tokens: 256
  metadata_model: 'llama-3.3-70b-versatile'
```

These values are illustrative only until explicit loading is implemented.

## Version pinning

`version.txt` holds the image tag used by the `build-*`, `tag-*`, and `push-*` Makefile
targets. Bump it before building images you intend to push.
