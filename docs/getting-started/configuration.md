# Configuration

Configuration comes from two places: secrets and endpoints in `.env`, and model behaviour
in `config.yaml`.

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
| `LANGSMITH_TRACING` | `true` or `false` |
| `LANGSMITH_ENDPOINT` | LangSmith API endpoint |
| `LANGSMITH_API_KEY` | LangSmith API key |
| `LANGSMITH_PROJECT` | LangSmith project name |

!!! danger "Never commit `.env`"
    `.env` is gitignored. On Azure, inject the same values through
    **App Service → Configuration** rather than baking them into an image.

Docker Compose adds two more at runtime: `REDIS_HOST` and `REDIS_PORT` point the backend
and the ingestion worker at the `redis` service, and the frontend gets `API_URL=http://api:8000`.

## `config.yaml`

Model behaviour that is not a secret lives in `config.yaml` at the repository root:

```yaml
collection: 'test_collection_oai_test'

groq:
  summarization_model: 'llama-3.3-70b-versatile'
  summarization_prompt: 'Summarize the following text: {{text}}'
  temperature: 0.3
  max_tokens: 256
  metadata_model: 'llama-3.3-70b-versatile'
```

- `collection` — the Qdrant collection the pipeline reads from.
- `groq.summarization_*` — model, prompt, and sampling settings used when conversation
  history is compacted, and when ingested chunks are summarized.
- `groq.metadata_model` — the model used for structured metadata extraction during ingestion.

Loading is handled by [`src.api.core.config`](../reference/api.md#configuration), which merges
the YAML file with the environment.

## Version pinning

`version.txt` holds the image tag used by the `build-*`, `tag-*`, and `push-*` Makefile
targets. Bump it before building images you intend to push.
