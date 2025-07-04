# RAG demo

**Objective**: Deploy a Streamlit app (as a Docker container) that allows the user to query a large amount of PDF documents that are pre-loaded into a Vector Store (Qdrant). 

Basically the 2 main steps are:

1. Upload folder containing many PDFs into the Qdrant VS database

The ingestion of the PDF folder into Qdrant is done using `make ingest`

2. Query the Qdrant Vector Store database

The app is served locally using `make serve` 

**Docker image**: to create & run it:

* docker build -t rag-demo:0.0.1 .
* docker run -p 8501:8501 --env-file .env rag-demo:0.0.1
* docker image tag rag-app:0.0.1 pdemeulenaer/rag-demo:0.0.1
* docker login
* docker image push pdemeulenaer/rag-demo:0.0.1

TODO: indicate to the Docker container what is the address of the Qdrant VS

## Dependencies

The APIs used by this project are mainly (see config.yaml for exact definitions):

* groq.com (for text summarization and for text generation)
* cohere (for reranking of retrieved chunks)
* Qdrant Cloud vector database
* custom embedding model API deployed at https://rag-gbdgccage7bkgwa8.northeurope-01.azurewebsites.net/

The corresponding API keys should be added in .env file (derived from .env.sample)