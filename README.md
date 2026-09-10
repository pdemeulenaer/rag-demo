# 📚 RAG Demo – Streamlit + FastAPI + Qdrant

This project demonstrates a modular Retrieval-Augmented Generation (RAG) system for querying large collections of PDF documents via a web-based chat interface.  The system is designed to be modular and leverages several state-of-the-art APIs and technologies for efficient and accurate information retrieval and generation.

---

## 🏗️ Architecture Overview

The application is composed of several key components:

- **Frontend**: A **Streamlit** chat interface communicating with the backend API.
- **Backend API**: A **FastAPI** server orchestrating the RAG pipeline, handling queries, conversation history, and service integration.
- **Embedding Model**: OpenAI's text-embedding-3-small.- 
- **Vector Database**: A **Qdrant Cloud** vector database stores document embeddings and metadata for hybrid (semantic + exact keyword matching) search.
- **Reranker**: **Cohere's Rerank API** improves relevance of retrieved chunks before LLM generation.- 
- **LLM for Generation**: Groq (`llama-3.3-70b-versatile`) or OpenAI (`gpt-4.1-nano`, `gpt-4.1-mini`, `gpt-5-nano`) LLMs can be selected to generate answers based on retrieved context.

---



## Key Features

*   **Conversational Chat**: Engages in a multi-turn dialogue, maintaining context through a conversation memory system.
*   **PDF Knowledge Base**: Users can upload and process a large collection of PDF documents.
*   **Hybrid Search**: Combines semantic (vector) search with traditional keyword search for more robust retrieval. Re-ranking is performed on top of this.
*   **Advanced RAG Pipeline**:
    *   Retrieves relevant text chunks from Qdrant (hybrid search)
    *   Reranks the retrieved chunks using Cohere for better context.
    *   Constructs a detailed prompt including the query, chat history, and relevant context.
    *   Generates a comprehensive answer using Groq's LLM.
*   **Source Citation**: Answers include references to the source documents (including author, title, year, and page numbers) from which the information was extracted.
*   **Conversation Memory**: Implements a sliding window with summarization on the backend to manage long conversations efficiently without losing context.
*   **Multi-user sessions**: a Redis database ensures that multiple users can chat independently with the RAG.

## Setup and Installation

1.  **Prerequisites**:
    *   Python 3.12+
    *   Docker & Docker Compose
    *   Docker Desktop >=v4.44.0 (optional)
    *   `make`

2.  **Clone the Repository**:
    ```bash
    git clone https://github.com/pdemeulenaer/rag-demo.git
    cd rag-demo
    ```

3.  **Environment Variables**:
    Copy the sample and fill in required keys/URLs:
     ```bash
     cp .env.sample .env
     ```

    You will need to populate the following variables in your `.env` file:

    - `GROQ_API_KEY`: API key for Groq (LLM generation)
    - `QDRANT_API_KEY`: API key for Qdrant Cloud
    - `QDRANT_URL`: URL for your Qdrant Cloud instance
    - `QDRANT_COLLECTION_NAME`: Name of your Qdrant collection
    - `EMBEDDING_API_URL`: URL for your embedding model API
    - `COHERE_API_KEY`: API key for Cohere (reranking)
    - `OPENAI_API_KEY`: API key for OpenAI (if using OpenAI models)
    - `EMBEDDING_MODEL`: Embedding model name (e.g., `text-embedding-3-small`)
    - `EMBEDDING_MODEL_PROVIDER`: Embedding model provider (e.g., `openai`)
    - `GENERATION_MODEL`: Generation model name (e.g., `gpt-4.1`)
    - `GENERATION_MODEL_PROVIDER`: Generation model provider (e.g., `openai`)
    - `LANGSMITH_TRACING`: Enable LangSmith tracing (`true` or `false`)
    - `LANGSMITH_ENDPOINT`: LangSmith API endpoint
    - `LANGSMITH_API_KEY`: LangSmith API key
    - `LANGSMITH_PROJECT`: LangSmith project name


4. **Install Dependencies**
   - Recommended: use a Python virtual environment together with `uv` package manager:

     ```bash
     python -m venv .venv
     source .venv/bin/activate
     uv init
     uv sync
     ```

## 📥 Usage

**Run the Application locally**

- Start backend API and Streamlit frontend with Docker Compose:

  ```bash
  make compose
  ```

  `make compose` runs the API and ingestion worker with your host UID/GID, so their
  shared `temp_uploads` directory is writable without manually changing ownership.
  If you run Docker Compose directly, supply the same values explicitly:

  ```bash
  LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose up --build
  ```

- Access UI: [http://localhost:8501](http://localhost:8501)
- Access API: [http://localhost:8000/docs](http://localhost:8000/docs)
- Both frontend and backend logs can be investigated in the Docker Desktop containers

---

## arXiv ingestion and PostgreSQL

Both manual uploads and arXiv papers now share the PostgreSQL catalogue. Streamlit's
**Document inventory → All sources** lists them together with their processing states;
**Query source** independently controls which corpus answers your question.

**Existing installations:** follow the [catalogue upgrade guide](docs/operations/catalogue.md)
to migrate the schema and register existing upload vectors without re-embedding:

```bash
make papers-backup
make papers-init-db
make papers-import-uploads LEGACY_MODEL=text-embedding-3-small
make papers-audit
```

Quiesce ingestion before backup/migration; the guide includes service
stop/recreation and legacy Batch-job precautions. PostgreSQL is now required for both
ingestion paths. `papers-audit` is read-only and never repairs or re-embeds automatically.
`make papers-backup` creates and checks a local catalogue archive in `~/rag-demo-backups`;
`make papers-backups` lists them. It does not back up Qdrant or PDF/image files.

The [arXiv setup and operation guide](docs/getting-started/arxiv.md) covers the
star-cluster scope, PostgreSQL catalogue, PDF processing, daily scheduling and
Vanilla/Hybrid comparison. Run `make papers-help` to see the command shortcuts.

For monitored daily automation, see the [short Airflow setup guide](docs/operations/daily-ingestion.md).
`make airflow-up` starts the optional local scheduler with a **new DAG paused**;
alerts are optional locally. Explicitly unpause the DAG to authorize paid daily ingestion.
`make papers-run-status` displays the durable run summary.

Merge the paper settings from `.env.sample` into your existing `.env` first; do not
overwrite your keys. These targets run the Python CLI on your host and PostgreSQL
in its own Docker container. Use `localhost` in the host `PAPERS_DATABASE_URL`.

```bash
make papers-preview DAYS=7    # Metadata preview only: does NOT populate PostgreSQL
make papers-db-up             # Start PostgreSQL and wait until healthy
make papers-init-db           # Create catalogue tables
make papers-backfill DAYS=7   # Save matching metadata and queue processing
make papers-status            # Matching papers should now be pending

# Opt-in: downloads PDFs and incurs embedding API usage
make papers-process LIMIT=2
make papers-status            # Successfully indexed papers are ready to query
```

PostgreSQL data persists in the Docker volume `papers_postgres`. PDF/text artifacts
use `data/paper_artifacts/` by default (or Azure Blob when configured); embeddings
go to the separate `PAPERS_COLLECTION` in Qdrant. Select the arXiv corpus in Streamlit
after papers become `ready`.

Later, use `make papers-sync` for metadata updates only, or `make papers-daily LIMIT=10`
for one discovery-and-processing run. Neither command installs a schedule.

## 🌐 Deployment to Azure (Multi-Container)

This project uses **`docker-compose.prod.yml`** for deployment. The CI/CD pipeline:

1. Builds and pushes `rag-frontend` + `rag-backend` images to Docker Hub.
2. Updates `docker-compose.prod.yml` with the correct image tags & staging API URL.
3. Deploys the multi-container app to Azure Web App staging slot.

---

## 🔧 Project Structure

```
.
├── src/
│   ├── api/              # FastAPI backend
│   └── chatbot_ui/       # Streamlit frontend
├── docker-compose.yml     # Local dev setup
├── docker-compose.prod.yml # Azure deployment
├── Dockerfile.fastapi
├── Dockerfile.streamlit
├── .env.sample
├── Makefile
└── version.txt
```

---

## 📝 Notes

* All environment variables are configured via `.env`.
* On Azure, secrets should be injected via **App Service > Configuration**.
* For staging deployments, a slot-specific API URL is injected automatically in the CI/CD pipeline.

---

## 📌 TODOs

### Functionalities to add

* [ ] Use Langfuse in container
* [ ] Add (Airflow pipeline) daily ingest for a particular topic

### Functionalities to correct/improve

Rag FastAPI:

Streamlit/frontend:


Qdrant:
* [ ] Improve error handling when backend cannot connect to Qdrant.
* [ ] Save Qdrant content into local/cloud based storage for backup & fast re-enablement if Qdrant Cloud cluster goes down after inactivity
* [ ] Allow local Qdrant cluster for testing

Context retrieval:
* [ ] Add question rephrasing

Observability:
* [ ] Add support for authentication in Streamlit UI.

Deployment & setup monitoring:
* [ ] Add monitoring/logging in Azure deployment.



## License

MIT
