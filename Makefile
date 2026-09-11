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
	uv run --group dev --group frontend pytest tests/unit -q

docs:
	uv run --group dev mkdocs serve -a 127.0.0.1:$(PORT)

docs-build:
	uv run --group dev mkdocs build

docs-deploy:
	uv run mkdocs gh-deploy --force

# Opt-in arXiv workflow. The CLI runs on the host; PostgreSQL runs in Compose.
# Omitted DAYS/LIMIT preserve the CLI/.env defaults. UNTIL is for backfills only.
PAPERS_CLI := uv run python -m src.api.papers
PAPERS_BACKFILL_ARGS = $(if $(DAYS),--days "$(DAYS)") $(if $(UNTIL),--until "$(UNTIL)")
PAPERS_PROCESS_ARGS = $(if $(LIMIT),--limit "$(LIMIT)")
PAPERS_SCHEDULE_CLI := uv run python -m src.api.papers.schedule
PAPERS_RUN_ARGS = $(if $(RUN_DATE),--run-date "$(RUN_DATE)") $(PAPERS_PROCESS_ARGS)

BACKUP_DIR ?= $(HOME)/rag-demo-backups
.PHONY: papers-backup papers-backups papers-backup-check
# Export paths as values, never interpolate user paths into shell commands.
papers-backup papers-backups papers-backup-check: export PAPERS_BACKUP_DIR := $(BACKUP_DIR)
papers-backup-check: export PAPERS_BACKUP_FILE := $(FILE)

papers-backup:
	python3 scripts/papers_backup.py backup

papers-backups:
	python3 scripts/papers_backup.py list

papers-backup-check:
	python3 scripts/papers_backup.py check

.PHONY: papers-scheduled papers-run-status airflow-up airflow-stop airflow-logs airflow-check

# Explicit paid run; fixes today's selection across retries, audits and reports.
papers-scheduled:
	$(PAPERS_SCHEDULE_CLI) all $(PAPERS_RUN_ARGS)

papers-run-status:
	$(PAPERS_SCHEDULE_CLI) status $(if $(RUN_DATE),--run-date "$(RUN_DATE)")

# New DAGs start PAUSED. Previously unpaused DAGs retain their state on restart.
airflow-up:
	mkdir -p data/paper_artifacts
	LOCAL_UID="$(LOCAL_UID)" docker compose --profile airflow up -d --build airflow

airflow-stop:
	docker compose --profile airflow stop airflow

airflow-logs:
	docker compose --profile airflow logs --tail=100 -f airflow

# Inspect the output: it must contain no DAG import errors. Does not trigger tasks.
airflow-check:
	docker compose --profile airflow exec airflow airflow dags list-import-errors --output json

.PHONY: papers-help papers-scope papers-preview papers-db-up papers-init-db \
        papers-backfill papers-process papers-sync papers-daily papers-status papers-count papers-audit papers-import-uploads

papers-help:
	@printf '%s\n' \
	  'arXiv workflow (host CLI, separate PostgreSQL container):' \
	  '  make papers-scope                    Show category/topic configuration' \
	  '  make papers-preview DAYS=7           Preview metadata only; no DB writes' \
	  '  make papers-db-up                    Start PostgreSQL and wait for health' \
	  '  make papers-backup                   Create/check a timestamped local PostgreSQL backup' \
	  '  make papers-backups                  List backups (default: ~/rag-demo-backups)' \
	  '  make papers-backup-check FILE=...    Recheck an archive without restoring it' \
	  '  make papers-init-db                  Create catalogue tables' \
	  '  make papers-backfill DAYS=7          Save metadata and queue papers' \
	  '  make papers-status                   Inspect processing states' \
	  '  make papers-count                    Count ready documents across arXiv and uploads' \
	  '  make papers-audit                    Read-only SQL/Qdrant consistency audit' \
	  '  make papers-import-uploads LEGACY_MODEL=text-embedding-3-small' \
	  '                                       Register existing upload vectors in SQL; no re-embedding' \
	  '  make papers-process LIMIT=2          Download/index pending PDFs (paid embeddings)' \
	  '  make papers-sync                     Discover metadata updates only' \
	  '  make papers-daily LIMIT=10           Sync + process once (paid embeddings)' \
	  '  make papers-scheduled LIMIT=10       Durable daily budget + audit + notifications (paid)' \
	  '  make papers-run-status              Read saved daily run summary/state' \
	  '  make airflow-up                     Start optional Airflow; new DAG is paused' \
	  '  make airflow-logs / airflow-stop     Inspect / stop scheduler' \
	  'DAYS/LIMIT are optional; omitted values use CLI/.env defaults.' \
	  'Preview/backfill also accept UNTIL=YYYY-MM-DD. No target installs a schedule.' \
	  'Guide: docs/getting-started/arxiv.md'

papers-scope:
	$(PAPERS_CLI) scope

papers-preview:
	$(PAPERS_CLI) backfill --dry-run $(PAPERS_BACKFILL_ARGS)

papers-db-up:
	docker compose --profile papers up -d --wait postgres

papers-init-db:
	$(PAPERS_CLI) init-db

papers-backfill:
	$(PAPERS_CLI) backfill $(PAPERS_BACKFILL_ARGS)

# Explicit opt-in to PDF downloads and embedding API usage.
papers-process:
	$(PAPERS_CLI) process $(PAPERS_PROCESS_ARGS)

papers-sync:
	$(PAPERS_CLI) sync

# One invocation only; does not install or enable a daily schedule.
papers-daily:
	$(PAPERS_CLI) daily $(PAPERS_PROCESS_ARGS)

papers-status:
	$(PAPERS_CLI) status

papers-count:
	@$(PAPERS_CLI) count

papers-audit:
	$(PAPERS_CLI) audit

papers-import-uploads:
	$(PAPERS_CLI) import-uploads $(if $(LEGACY_MODEL),--legacy-embedding-model "$(LEGACY_MODEL)")

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

EVAL_DIR ?= data/evaluation/star-clusters
EVAL_MODEL ?= gpt-4.1-mini
EVAL_MAX_TOKENS ?= 2500
EVAL_SOURCE ?= arxiv
QUESTIONS ?= 50
PAPERS ?= 50
EVAL_SEED ?= 42

.PHONY: eval-preview eval-check create-eval-dataset

# Freeze active paper evidence locally. No model calls or database writes.
eval-preview:
	uv run python -m evals.generate_questions prepare --output "$(EVAL_DIR)" --source "$(EVAL_SOURCE)" --questions "$(QUESTIONS)" --papers "$(PAPERS)" --seed "$(EVAL_SEED)" --model "$(EVAL_MODEL)" --max-completion-tokens "$(EVAL_MAX_TOKENS)"

# Explicit paid generation; resumes completed calls, never uploads to LangSmith.
create-eval-dataset:
	uv run python -m evals.generate_questions generate --output "$(EVAL_DIR)" $(if $(EVAL_WAIT_SECONDS),--wait-seconds "$(EVAL_WAIT_SECONDS)") $(if $(RETRY_JOB),--retry-job "$(RETRY_JOB)")

# Read-only model metadata request; no inference or changes to saved evaluation data.
eval-check:
	uv run python -m evals.generate_questions check --output "$(EVAL_DIR)"

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
	mkdir -p data/paper_artifacts temp_uploads
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
