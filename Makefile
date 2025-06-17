.ONESHELL:

SHELL := $(shell which bash)

# Image name
IMAGE_NAME := rag-demo

# Read version from version.txt
VERSION := $(shell cat version.txt)

DOCKER_FOLDER := pdemeulenaer

# 0. General local commands

env-file:
	cp .env.sample .env
	@echo "Created .env file from .env.sample"

install:
	poetry install
	poetry lock
	@echo "Installed dependencies with Poetry"

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
	poetry run python -m src.rag_demo.ingest_to_qdrant

serve:
	poetry run streamlit run src/rag_demo/app.py	

evaluate:
	poetry run python src/rag_demo/evaluation_ragas.py		


.PHONY: build run

build:
	@echo "Building image version: $(VERSION)"
	@docker build -t $(IMAGE_NAME):$(VERSION) .
	@echo "Built image: $(IMAGE_NAME):$(VERSION)"

run:
	@echo "Running image version: $(VERSION)"
	@docker run -d -p 8501:8501 --env-file .env --name $(IMAGE_NAME) $(IMAGE_NAME):$(VERSION)
	@echo "Running image: $(IMAGE_NAME):$(VERSION)"
	@echo "Access the app at http://localhost:8501"

tag:
	@echo "Tag image version: $(VERSION)"
	@docker tag $(IMAGE_NAME):$(VERSION) $(DOCKER_FOLDER)/$(IMAGE_NAME):$(VERSION)
	@echo "Tagged image: $(DOCKER_FOLDER)/$(IMAGE_NAME):$(VERSION)"

push:
	@echo "Pushing image version: $(VERSION)"
	@docker push $(DOCKER_FOLDER)/$(IMAGE_NAME):$(VERSION)
	@echo "Pushed image: $(DOCKER_FOLDER)/$(IMAGE_NAME):$(VERSION)"		

