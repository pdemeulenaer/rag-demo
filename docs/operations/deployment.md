# Deployment

## Local — Docker Compose

```bash
make compose            # docker compose up -d --build
```

`docker-compose.yml` defines four services:

| Service | Image / command | Ports | Notes |
| --- | --- | --- | --- |
| `streamlit-app` | `Dockerfile.streamlit` | 8501 | `API_URL=http://api:8000`, source mounted for live reload |
| `api` | `Dockerfile.fastapi` | 8000 | Healthcheck on `/health`, waits for Redis |
| `ingestion-worker` | same image, `python -m src.api.ingestion.poller` | — | Healthcheck via `src.api.healthcheck`, waits for a healthy API |
| `redis` | `redis:7.0-alpine` | 6379 | Named volume `redis_data`, `redis-cli ping` healthcheck |

Both application services bind-mount their source directory, so code changes are picked up
without a rebuild. `./temp_uploads` is shared between the API and the worker so uploaded PDFs
are visible to both.

A local Qdrant service is present but commented out — the default configuration points at
Qdrant Cloud via `QDRANT_URL`. Uncomment it (and the `QDRANT_URL=http://qdrant:6333`
environment line) to run entirely offline.

Verify a running stack with:

```bash
./verify_stack.sh
```

## Images

Image tags come from `version.txt`:

```bash
make build-ui      && make tag-ui      && make push-ui
make build-fastapi && make tag-fastapi && make push-fastapi
```

Images are published under the `pdemeulenaer` Docker Hub namespace as `rag-frontend` and
`rag-backend`.

## Azure — multi-container Web App

Deployment uses `docker-compose.prod.yml`. The CI/CD pipeline:

1. Builds and pushes `rag-frontend` and `rag-backend` to Docker Hub.
2. Rewrites `docker-compose.prod.yml` with the correct image tags and the staging API URL.
3. Deploys the multi-container app to the Azure Web App staging slot.

!!! warning "Secrets on Azure"
    Do not ship `.env` into the image. Inject the values through
    **App Service → Configuration**. For staging deployments the slot-specific API URL is
    injected automatically by the pipeline.

## Known gaps

- Monitoring and logging in the Azure deployment are not yet set up.
- Error handling when the backend cannot reach Qdrant needs hardening.
- The Streamlit UI has no authentication.
