.ONESHELL:

SHELL := $(shell which bash)

# Image name
FRONTEND_IMAGE_NAME := rag-backend
BACKEND_IMAGE_NAME := rag-frontend

# Read version from version.txt
VERSION := $(shell cat version.txt)

DOCKER_FOLDER := pdemeulenaer
LOCAL_UID := $(shell id -u)
LOCAL_GID := $(shell id -g)

# Port for the MkDocs development server
PORT ?= 8000

# 0. General local commands

env-file:
	cp .env.sample .env
	@echo "Created .env file from .env.sample"

install:
# 	uv install
# 	poetry lock
# 	@echo "Installed dependencies with Poetry"
	uv init
	uv sync
	uv lock
	@echo "Installed dependencies with uv"

# pre-commit:
# 	pre-commit install

setup: env-file install #pre-commit

black:
	black .

lint:
	mypy src
	pylint src

test:
	uv run --group dev pytest tests/unit -q

docs:
	uv run --group dev mkdocs serve -a 127.0.0.1:$(PORT)

docs-build:
	uv run --group dev mkdocs build

docs-deploy:
	uv run mkdocs gh-deploy --force

# quality: black lint test

# quality-ci: lint test

ingest:
	uv run python -m ingestion_batch.ingest_to_qdrant_oai
# 	uv run python ./ingestion/ingest_to_qdrant_oai.py

run-api:
# 	uv run uvicorn src.api.main:app --reload --port 8000
	uv run python run_with_env.py

serve:
# 	uv run streamlit run src/rag_demo/app.py
	uv run --group frontend streamlit run src/chatbot_ui/main.py

# evaluate: # TODO: take from other repo
# 	uv run python src/rag_demo/evaluation_ragas.py	

# inspect redis chat history # input parameter: chat id, like 80c35ffb-8d19-4b3c-b9d4-b2da0731e620
redis-chat:
	uv run python src/api/redis/inspect_redis.py 

create-eval-dataset:
	uv run --group eval python evals/eval_dataset_creation.py

run-evals:
	uv run --group eval python evals/eval_retriever.py


.PHONY: build run docs docs-build docs-deploy

# Frontend
build-ui:
	@echo "Building image version: $(VERSION)"
	@docker build -t $(FRONTEND_IMAGE_NAME):$(VERSION)  -f Dockerfile.streamlit .
	@echo "Built image: $(FRONTEND_IMAGE_NAME):$(VERSION)"

run-ui:
	@echo "Running image version: $(VERSION)"
	@docker run -d -p 8501:8501 --env-file .env --name $(FRONTEND_IMAGE_NAME) $(FRONTEND_IMAGE_NAME):$(VERSION)
	@echo "Running image: $(FRONTEND_IMAGE_NAME):$(VERSION)"
	@echo "Access the app at http://localhost:8501"

tag-ui:
	@echo "Tag image version: $(VERSION)"
	@docker tag $(FRONTEND_IMAGE_NAME):$(VERSION) $(DOCKER_FOLDER)/$(FRONTEND_IMAGE_NAME):$(VERSION)
	@echo "Tagged image: $(DOCKER_FOLDER)/$(FRONTEND_IMAGE_NAME):$(VERSION)"

push-ui:
	@echo "Pushing image version: $(VERSION)"
	@docker push $(DOCKER_FOLDER)/$(FRONTEND_IMAGE_NAME):$(VERSION)
	@echo "Pushed image: $(DOCKER_FOLDER)/$(FRONTEND_IMAGE_NAME):$(VERSION)"		


# Backend
build-fastapi:
	@echo "Building image version: $(VERSION)"
	@docker build -t $(BACKEND_IMAGE_NAME):$(VERSION) -f Dockerfile.fastapi .
	@echo "Built image: $(BACKEND_IMAGE_NAME):$(VERSION)"

run-fastapi:
	@echo "Running image version: $(VERSION)"
	@docker run -d -p 8000:8000 --env-file .env --name $(BACKEND_IMAGE_NAME) $(BACKEND_IMAGE_NAME):$(VERSION)
	@echo "Running image: $(BACKEND_IMAGE_NAME):$(VERSION)"
	@echo "Access the app at http://localhost:8000"

tag-fastapi:
	@echo "Tag image version: $(VERSION)"
	@docker tag $(BACKEND_IMAGE_NAME):$(VERSION) $(DOCKER_FOLDER)/$(BACKEND_IMAGE_NAME):$(VERSION)
	@echo "Tagged image: $(DOCKER_FOLDER)/$(BACKEND_IMAGE_NAME):$(VERSION)"

push-fastapi:
	@echo "Pushing image version: $(VERSION)"
	@docker push $(DOCKER_FOLDER)/$(BACKEND_IMAGE_NAME):$(VERSION)
	@echo "Pushed image: $(DOCKER_FOLDER)/$(BACKEND_IMAGE_NAME):$(VERSION)"		


compose:
	@echo "Running docker-compose up"
	@LOCAL_UID="$(LOCAL_UID)" LOCAL_GID="$(LOCAL_GID)" docker compose up -d --build
	@api_container="$$(docker compose ps -q api)"; \
	api_health="$$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$$api_container")"; \
	if [ "$$api_health" = "healthy" ]; then \
		echo "Docker Compose is healthy on this Docker host."; \
		echo "From this host: Streamlit http://127.0.0.1:8501 | API http://127.0.0.1:8000"; \
		echo "From another device or remote IDE, localhost points to that client; use the Docker host address or a forwarded port instead."; \
	else \
		echo "Docker Compose started, but the API is $$api_health. Check 'docker compose logs api' and your Qdrant configuration." >&2; \
		docker compose ps >&2; \
		exit 1; \
	fi
