.ONESHELL:

SHELL := $(shell which bash)

# Image name
FRONTEND_IMAGE_NAME := rag-backend
BACKEND_IMAGE_NAME := rag-frontend

# Read version from version.txt
VERSION := $(shell cat version.txt)

DOCKER_FOLDER := pdemeulenaer

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
	behave tests/features/

# doc: 
# 	mkdocs build	

# quality: black lint test

# quality-ci: lint test

ingest:
	uv run python -m ingestion.ingest_to_qdrant_oai

run-api:
# 	uv run uvicorn src.api.main:app --reload --port 8000
	uv run python run_with_env.py

serve:
# 	uv run streamlit run src/rag_demo/app.py
	uv run streamlit run src/chatbot_ui/main.py	

# evaluate: # TODO: take from other repo
# 	uv run python src/rag_demo/evaluation_ragas.py	

# inspect redis chat history # input parameter: chat id, like 80c35ffb-8d19-4b3c-b9d4-b2da0731e620
redis-chat:
	uv run python src/api/redis/inspect_redis.py 

create-eval-dataset:
	uv run python evals/eval_dataset_creation.py

run-evals:
	uv run python evals/eval_retriever2.py	


.PHONY: build run

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
	@docker compose up -d --build
	@echo "Docker Compose is running. Access the frontend at http://localhost:8501 and backend at http://localhost:8000"

