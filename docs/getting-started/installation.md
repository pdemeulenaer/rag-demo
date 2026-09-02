# Installation

## 1. Clone the repository

```bash
git clone https://github.com/pdemeulenaer/rag-demo.git
cd rag-demo
```

## 2. Create the environment file

```bash
make env-file       # cp .env.sample .env
```

Fill in the keys described in [Configuration](configuration.md) before starting anything.

## 3. Install dependencies

The project uses `uv`:

```bash
make install        # uv init && uv sync && uv lock
```

`make setup` runs the environment file and dependency steps together.

!!! warning "Heavy dependency"
    `docling` pulls in PyTorch with a CUDA backend, so the first sync downloads several
    gigabytes. See [Benchmarks](../operations/benchmarks.md) for what that buys you.

## 4. Run the stack

### Everything at once (recommended)

```bash
make compose        # docker compose up -d --build
```

This starts four services: the Streamlit frontend, the FastAPI backend, the ingestion
worker, and Redis.

| Service | URL |
| --- | --- |
| Streamlit UI | <http://localhost:8501> |
| FastAPI docs | <http://localhost:8000/docs> |
| Qdrant dashboard (when run locally) | <http://localhost:6333/dashboard> |

### Individual processes

```bash
make run-api        # FastAPI backend via run_with_env.py
make serve          # Streamlit frontend
make ingest         # batch ingestion into Qdrant
```

## 5. Build the documentation

```bash
make docs                 # serve on http://127.0.0.1:8000
make docs PORT=8001       # serve on another port
make docs-build           # render the static site into site/
```

!!! tip "Port clash"
    The FastAPI backend also defaults to port 8000. Run the docs on another port
    (`make docs PORT=8001`) when the API is up.

## Other useful targets

| Command | What it does |
| --- | --- |
| `make black` | Format the codebase |
| `make lint` | `mypy` and `pylint` over `src` |
| `make test` | Run the Behave test suite |
| `make redis-chat` | Inspect a stored Redis chat history |
| `make create-eval-dataset` | Build the retrieval evaluation dataset |
| `make run-evals` | Run the retriever evaluation |
| `make build-ui` / `make build-fastapi` | Build the Docker images |
