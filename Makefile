.ONESHELL:

SHELL := $(shell which bash)

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

# setup: env-file conda pre-commit

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

