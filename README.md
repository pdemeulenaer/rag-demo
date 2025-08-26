# RAG demo

This project is a demonstration of a sophisticated Retrieval-Augmented Generation (RAG) system. It provides a web-based chat interface allowing users to ask questions against a knowledge base of PDF documents. The system is designed to be modular and leverages several state-of-the-art APIs and technologies for efficient and accurate information retrieval and generation.

## Architecture Overview

The application is composed of several key components:

*   **Frontend**: A user-friendly chat interface built with **Streamlit**. It communicates with the backend API to provide a seamless conversational experience.
*   **Backend API**: A **FastAPI** server that exposes endpoints for the RAG pipeline. It handles user queries, manages conversation history, and orchestrates the different services.
*   **Vector Database**: **Qdrant Cloud** is used as the vector store for storing document embeddings and metadata, enabling efficient semantic search.
*   **Embedding Model**: A custom embedding model served via its own API endpoint. This is responsible for converting text chunks and user queries into vector representations.
*   **LLM for Generation**: **Groq** provides the fast Large Language Model (`llama-3.3-70b-versatile`) for generating answers based on the retrieved context.
*   **Reranker**: **Cohere's Rerank API** is used to improve the relevance of retrieved document chunks before they are passed to the LLM, enhancing the quality of the generated answers.

## Key Features

*   **Conversational Chat**: Engages in a multi-turn dialogue, maintaining context through a conversation memory system.
*   **PDF Knowledge Base**: Ingests and processes a large collection of PDF documents.
*   **Hybrid Search**: Combines semantic (vector) search with traditional keyword search for more robust retrieval.
*   **Advanced RAG Pipeline**:
    *   Retrieves relevant text chunks from Qdrant.
    *   Reranks the retrieved chunks using Cohere for better context.
    *   Constructs a detailed prompt including the query, chat history, and relevant context.
    *   Generates a comprehensive answer using Groq's LLM.
*   **Source Citation**: Answers include references to the source documents (including author, title, year, and page numbers) from which the information was extracted.
*   **Conversation Memory**: Implements a sliding window with summarization on the backend to manage long conversations efficiently without losing context.

## Setup and Installation

1.  **Prerequisites**:
    *   Python 3.12+
    *   Docker & Docker Compose
    *   `make`

2.  **Clone the Repository**:
    ```bash
    git clone <repository-url>
    cd rag-demo
    ```

3.  **Environment Variables**:
    Create a `.env` file from the sample and fill in the required API keys and URLs.
    ```bash
    cp .env.sample .env
    ```
    You will need to populate the following variables in your `.env` file:
    *   `API_URL`: The URL for the backend API (e.g., `http://localhost:8000`).
    *   `EMBEDDING_API_URL`: The URL for your custom embedding model API.
    *   `QDRANT_URL`: The URL for your Qdrant Cloud instance.
    *   `QDRANT_API_KEY`: Your API key for Qdrant Cloud.
    *   `COLLECTION_NAME`: The name of the collection in Qdrant (e.g., `rag-demo-collection`).
    *   `GROQ_API_KEY`: Your API key for Groq.
    *   `COHERE_API_KEY`: Your API key for Cohere.
    *   `LANGCHAIN_API_KEY`: (Optional) For tracing with LangSmith.

4.  **Install Dependencies**:
    It is recommended to use a virtual environment.
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

## Usage

1.  **Ingest Documents**:
    Place your PDF files into a designated folder (e.g., `data/`). Then, run the ingestion process to process the documents and populate the Qdrant vector database.
    ```bash
    make ingest
    ```
    This command will parse the PDFs, chunk the text, generate embeddings, and upload them to your Qdrant collection.

2.  **Run the Application**:
    To start the backend API and the Streamlit frontend, use the `serve` command.
    ```bash
    make serve
    ```
    This will typically use `docker-compose` to launch all the necessary services. You can then access the chatbot UI at `http://localhost:8501`.

## Docker

The application is designed to be run with Docker.

*   **Build the Docker image**:
    ```bash
    docker build -t rag-demo:0.0.1 .
    ```

*   **Run the Docker container**:
    Make sure your `.env` file is present in the root directory.
    ```bash
    docker run -p 8501:8501 --env-file .env rag-demo:0.0.1
    ```
    *Note*: The Docker container needs to know the address of the Qdrant database and other services. Using `--env-file` passes the necessary environment variables. If your Qdrant instance is running on your host machine from the container's perspective, you might need to use `host.docker.internal` instead of `localhost` in your `QDRANT_URL`.

*   **Push to a Registry (Optional)**:
    To share your image, you can tag it and push it to a container registry like Docker Hub.
    ```bash
    docker image tag rag-demo:0.0.1 your-dockerhub-username/rag-demo:0.0.1
    docker login
    docker image push your-dockerhub-username/rag-demo:0.0.1
    ```






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