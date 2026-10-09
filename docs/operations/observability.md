# Observability with Langfuse

This repository uses its own optional **self-hosted Langfuse v4 Docker stack**. It does not
use LangSmith. When Langfuse is disabled, its SDK is not imported and tracing is a no-op.

## Start and configure it

```bash
make langfuse-up
```

Open <http://localhost:3000>, create the first account and a project, then create project
API keys. Put those keys in `.env`:

```dotenv
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=http://localhost:3000
LANGFUSE_BASE_URL_CONTAINER=http://langfuse-web:3000
LANGFUSE_ENVIRONMENT=local
LANGFUSE_RELEASE=
LANGFUSE_DATASET_PREFIX=scientific-paper-rag
```

`LANGFUSE_BASE_URL` is used by host commands such as `make eval-run`.
`LANGFUSE_BASE_URL_CONTAINER` is injected into the API and worker containers. Recreate the
application services after enabling tracing:

```bash
docker compose up -d --build api ingestion-worker
```

Useful operations:

```bash
make langfuse-status
make langfuse-logs
make langfuse-stop       # removes containers; preserves Langfuse volumes/data
```

The stack is defined in `docker-compose.langfuse.yaml` and contains Langfuse web/worker,
PostgreSQL, ClickHouse, Redis and MinIO. It joins the normal repository Compose network.
Only the UI (`127.0.0.1:3000`) and MinIO media endpoint (`127.0.0.1:9090`) bind to the host.

The supplied infrastructure secrets are local-demo defaults. Replace all
`LANGFUSE_*_PASSWORD`, `LANGFUSE_SALT`, `LANGFUSE_ENCRYPTION_KEY` and
`LANGFUSE_NEXTAUTH_SECRET` values before exposing or sharing the instance. Docker Compose
is suitable for this demo, but has no built-in high availability or backups.

## What is traced

An explicit one-shot request produces a hierarchy equivalent to:

```text
rag_request
└── rag_pipeline
    ├── retrieve_context
    │   └── OpenAI embedding
    ├── rerank_context          # hybrid_rerank only
    └── generate_answer
        └── OpenAI generation
```

An Agentic request adds its bounded orchestration beneath the same request/pipeline trace:

```text
rag_request
└── rag_pipeline
    ├── agentic_retrieval
    │   ├── LangGraph agent model call
    │   ├── LangGraph/LangChain tool call
    │   │   └── search/section/neighbour retriever span
    │   ├── bounded graph loop           # repeated only within hard limits
    │   └── validated execution metadata + stop reason
    └── generate_answer                  # only when evidence was judged sufficient
        └── configured answer generation
```

The Agentic trace records safe summaries, tool arguments, evidence IDs, budget usage,
model/token usage, latency and the terminal stop reason. It does not store private
chain-of-thought. Tool/model failure and insufficient evidence terminate before final
generation. The Streamlit execution panel shows a smaller safe subset and links no raw
prompts or evidence text.

Intent classification, chat-only follow-ups and conversation summaries are also observed.
Raw OpenAI SDK access is centralized in `src/api/core/clients.py`; Agentic orchestration uses
the standard `ChatOpenAI` integration so LangGraph can bind tools and Langfuse can receive its
callback events. Prompt and response content is stored by the local Langfuse stack, so
protect its access and persistent volumes accordingly.

Short-lived evaluation commands flush traces before exiting. The API flushes on graceful
shutdown. Langfuse transport errors are asynchronous and should not change an answer;
benchmark authentication is checked before paid calls when Langfuse is enabled because the
requested Dataset Experiment could not otherwise be recorded.

## Evaluation experiments

With Langfuse enabled, run:

```bash
make eval-run EVAL_DIR=data/evaluation/markdown-mini-v1 EVAL_LIMIT=2 EVAL_JUDGE=true
```

Look under **Datasets** for the content-addressed dataset and under its experiments/runs
for separate Vanilla, Hybrid, Hybrid + Rerank and Agentic results (or the subset selected
with `EVAL_MODES`). The local `manifest.json` records the Langfuse
dataset name, run names and returned URLs.
