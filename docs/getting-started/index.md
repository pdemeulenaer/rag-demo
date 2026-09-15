# Getting Started

This section covers everything needed to run the RAG demo on your own machine.

- [Installation](installation.md) — prerequisites, dependency install, and the ways to start the stack.
- [Configuration](configuration.md) — the `.env` variables and the `config.yaml` model settings.

## Prerequisites

- Python 3.12+
- Docker and Docker Compose (Docker Desktop ≥ v4.44.0 is optional but handy for logs)
- `make`
- [`uv`](https://docs.astral.sh/uv/) for dependency management

## The short version

```bash
git clone https://github.com/pdemeulenaer/rag-demo.git
cd rag-demo
make setup          # copies .env.sample to .env and installs dependencies
# fill in the API keys in .env
make compose        # builds and starts the whole stack
```

Then open the UI at <http://localhost:8501> and the API docs at <http://localhost:8000/docs>.
