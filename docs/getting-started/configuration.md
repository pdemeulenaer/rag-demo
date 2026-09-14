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
| `QDRANT_COLLECTION_NAME` | Collection holding the document embeddings |
| `EMBEDDING_API_URL` | Endpoint of the embedding model API |
| `EMBEDDING_MODEL` | Embedding model name, e.g. `text-embedding-3-small` |
| `EMBEDDING_MODEL_PROVIDER` | Embedding provider, e.g. `openai` |
| `GENERATION_MODEL` | Generation model name, e.g. `gpt-4.1` |
| `GENERATION_MODEL_PROVIDER` | Generation provider, e.g. `openai` |
| `COHERE_API_KEY` | Cohere API key, used for reranking |
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
