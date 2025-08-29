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
- **LLM for Generation**: Groq (`llama-3.3-70b-versatile`) generates answers based on retrieved context.

---



## Key Features

*   **Conversational Chat**: Engages in a multi-turn dialogue, maintaining context through a conversation memory system.
*   **PDF Knowledge Base**: Ingests and processes a large collection of PDF documents.
*   **Hybrid Search**: Combines semantic (vector) search with traditional keyword search for more robust retrieval. Re-ranking is performed on top of this.
*   **Advanced RAG Pipeline**:
    *   Retrieves relevant text chunks from Qdrant (hybrid search)
    *   Reranks the retrieved chunks using Cohere for better context.
    *   Constructs a detailed prompt including the query, chat history, and relevant context.
    *   Generates a comprehensive answer using Groq's LLM.
*   **Source Citation**: Answers include references to the source documents (including author, title, year, and page numbers) from which the information was extracted.
*   **Conversation Memory**: Implements a sliding window with summarization on the backend to manage long conversations efficiently without losing context.

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
    - `LANGSMITH_PROJECT`: LangSmith project name (e.g., `rag

4. **Install Dependencies**
   - Recommended: use a virtual environment
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     uv init
     uv sync
     ```

## Usage

## 📥 Usage

1. **Ingest Documents** [TODO]
   <!-- - Place PDFs in a folder (e.g., `data/`)
   - Run ingestion:
     ```bash
     make ingest
     ```
   - Parses PDFs, chunks text, generates embeddings, uploads to Qdrant. -->

2. **Run the Application**
   - Start backend API and Streamlit frontend with Docker Compose:
  
     ```bash
     docker-compose up --build
     ```

   - Access UI: [http://localhost:8501](http://localhost:8501)
   - Access API: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Both frontend and backend logs can be investigated in the Docker Desktop containers



# 📚 RAG Demo – Streamlit + FastAPI + Qdrant

**Objective**: Demonstrate a lightweight Retrieval-Augmented Generation (RAG) pipeline where users can query a collection of PDF documents pre-loaded into a **Qdrant Vector Store**.

The project consists of two Dockerized services:

* **Backend**: FastAPI service that handles embeddings, retrieval, and communication with external APIs.
* **Frontend**: Streamlit app that provides a simple chat-style interface to query the knowledge base.

---

## 🚀 Features

* Ingest a folder of PDFs into **Qdrant Cloud** with one command.
* Query documents using **RAG pipeline** with Groq (LLMs), Cohere (reranker), and a custom embedding model API.
* **Streamlit UI** for interactive exploration.
* **Dockerized** for local development and **multi-container deployment** to Azure Web App.

---

## 🛠️ Prerequisites

* Docker & Docker Compose
* Python ≥ 3.10 (if running outside Docker)
* Azure CLI (for deployment)

---

## ⚙️ Environment Setup

1. Copy the sample env file:

   ```bash
   cp .env.sample .env
   ```

2. Fill in your API keys inside `.env`:

   * `GROQ_API_KEY` → for text generation/summarization
   * `COHERE_API_KEY` → for reranking retrieved chunks
   * `QDRANT_API_KEY` → for Qdrant Cloud access
   * `QDRANT_URL` → your Qdrant cluster endpoint
   * `EMBEDDING_API_URL` → custom embedding model endpoint

---

## 📥 Step 1 – Ingest PDFs into Qdrant

Upload all your PDFs into Qdrant with:

```bash
make ingest
```

This processes and indexes the documents in your Qdrant collection.

---

## 💻 Step 2 – Run Locally

To serve the Streamlit UI and FastAPI backend locally:

```bash
make serve
```

Or directly with Docker Compose:

```bash
docker-compose up --build
```

* Streamlit app → [http://localhost:8501](http://localhost:8501)
* FastAPI backend → [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🐳 Docker Images

Build and run locally:

```bash
docker build -t rag-demo:0.0.1 .
docker run -p 8501:8501 --env-file .env rag-demo:0.0.1
```

Push to Docker Hub:

```bash
docker tag rag-demo:0.0.1 pdemeulenaer/rag-demo:0.0.1
docker push pdemeulenaer/rag-demo:0.0.1
```

---

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

* [ ] Add monitoring/logging in Azure deployment.
* [ ] Improve error handling when backend cannot connect to Qdrant.
* [ ] Add support for authentication in Streamlit UI.

## License

MIT