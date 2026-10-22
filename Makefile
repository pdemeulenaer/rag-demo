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
	uv run --group dev --group frontend python -m pytest tests/unit -q

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

.PHONY: papers-scheduled papers-run-status airflow-up airflow-stop airflow-logs airflow-check airflow-password

# Explicit paid run; fixes today's selection across retries, audits and reports.
papers-scheduled:
	$(PAPERS_SCHEDULE_CLI) all $(PAPERS_RUN_ARGS)

papers-run-status:
	$(PAPERS_SCHEDULE_CLI) status $(if $(RUN_DATE),--run-date "$(RUN_DATE)")

# New DAGs start PAUSED. Previously unpaused DAGs retain their state on restart.
airflow-up:
	mkdir -p data/paper_artifacts
	LOCAL_UID="$(LOCAL_UID)" docker compose --profile airflow up -d --build airflow
	@echo "Airflow UI: http://localhost:8080"

airflow-stop:
	docker compose --profile airflow stop airflow

airflow-logs:
	docker compose --profile airflow logs --tail=100 -f airflow

airflow-password:
	docker compose --profile airflow exec airflow cat /opt/airflow/simple_auth_manager_passwords.json.generated

# Inspect the output: it must contain no DAG import errors. Does not trigger tasks.
airflow-check:
	docker compose --profile airflow exec airflow airflow dags list-import-errors --output json

# Langfuse is opt-in, but uses the normal Compose project/network so the API can
# address it as http://langfuse-web:3000. Stop removes containers, not data volumes.
LANGFUSE_COMPOSE := docker compose -f docker-compose.yml -f docker-compose.langfuse.yaml
LANGFUSE_SERVICES := langfuse-web langfuse-worker langfuse-postgres langfuse-clickhouse langfuse-redis langfuse-minio

.PHONY: langfuse-up langfuse-stop langfuse-status langfuse-logs

langfuse-up:
	$(LANGFUSE_COMPOSE) up -d --wait langfuse-web langfuse-worker

langfuse-stop:
	$(LANGFUSE_COMPOSE) stop $(LANGFUSE_SERVICES)
	$(LANGFUSE_COMPOSE) rm -f $(LANGFUSE_SERVICES)

langfuse-status:
	$(LANGFUSE_COMPOSE) ps $(LANGFUSE_SERVICES)

langfuse-logs:
	$(LANGFUSE_COMPOSE) logs --tail=100 -f langfuse-web langfuse-worker

# KG phases 8.1–8.2: optional database, free preparation and explicit paid extraction.
KG_COMPOSE := docker compose -f docker-compose.kg.yml --profile kg
KG_SNAPSHOT ?= data/evaluation/markdown-mini-v4/snapshot.json
KG_SELECTION ?= pilot
KG_PILOT ?= src/api/kg/pilot.json
KG_DIR ?= data/knowledge_graph/pilot-v1
KG_PAPERS ?=
KG_SOURCE ?= arxiv
KG_TERM ?=
KG_PAGE_SIZE ?= 20
KG_AFTER ?=
KG_PAPER_IDS ?=
KG_INCLUDE_PILOT ?= true
KG_SELECTION_FILE ?=
KG_MAX_CALLS ?=
KG_RETRY_FAILED ?= false
KG_FAILED_ONLY ?= false
KG_CHUNKS_PER_PAPER ?=
KG_REVIEW ?= review.json
KG_RECORD_ID ?=
KG_DECISION ?=
KG_REVIEWER ?=
KG_REASON ?=
KG_NOTES ?=
KG_GRAPH ?=
KG_EXPECT_ACTIVE ?= none
.PHONY: kg-publish-preview kg-publish kg-publication-verify kg-activate kg-publication-status kg-test-neo4j
.PHONY: kg-up kg-stop kg-status kg-password kg-logs kg-preview kg-schema kg-catalogue kg-select kg-prepare-preview kg-prepare kg-extract kg-validate kg-test kg-help kg-review-prepare kg-review-set kg-review-validate kg-review-export

kg-up:
	set -e
	$(KG_COMPOSE) up -d --wait neo4j
	@echo "Neo4j Browser: http://localhost:7474 (username: neo4j)"

kg-stop:
	$(KG_COMPOSE) stop neo4j

kg-status:
	$(KG_COMPOSE) ps neo4j

# Local credential reminder only; does not reset or verify the persisted password.
kg-password:
	@set -e
	$(KG_COMPOSE) exec -T neo4j sh -c 'auth="$${NEO4J_AUTH:?NEO4J_AUTH is not set}"; printf "Username: %s\nPassword: %s\n" "$${auth%%/*}" "$${auth#*/}"'
	echo "Neo4j Browser: http://localhost:7474"
	echo "Configured initial credentials only: changing .env does not reset an existing database password. Do not share this output."

kg-logs:
	$(KG_COMPOSE) logs --tail=100 -f neo4j

kg-preview:
	uv run python -m src.api.kg preview --snapshot "$(KG_SNAPSHOT)" --selection "$(KG_SELECTION)" --pilot "$(KG_PILOT)"

kg-schema:
	uv run python -m src.api.kg schema

kg-catalogue:
	uv run python -m src.api.kg catalogue --source "$(KG_SOURCE)" --limit "$(KG_PAGE_SIZE)" $(if $(KG_TERM),--term "$(KG_TERM)",) $(if $(KG_AFTER),--after "$(KG_AFTER)",)

kg-select:
	uv run python -m src.api.kg select --output "$(KG_DIR)/selection.json" $(if $(filter true,$(KG_INCLUDE_PILOT)),--include-pilot "$(KG_PILOT)",) $(foreach id,$(KG_PAPER_IDS),--paper-id "$(id)")

# The new preview defaults to the manifest in KG_DIR; no files/services are written.
kg-prepare-preview:
	uv run python -m src.api.kg prepare-preview --selection-file "$(if $(KG_SELECTION_FILE),$(KG_SELECTION_FILE),$(KG_DIR)/selection.json)" $(if $(KG_CHUNKS_PER_PAPER),--chunks-per-paper "$(KG_CHUNKS_PER_PAPER)",) $(if $(KG_MAX_CALLS),--max-calls "$(KG_MAX_CALLS)",)

kg-prepare:
	uv run --group kg python -m src.api.kg prepare $(if $(KG_SELECTION_FILE),--selection-file "$(KG_SELECTION_FILE)",--snapshot "$(KG_SNAPSHOT)" --selection "$(KG_SELECTION)" --pilot "$(KG_PILOT)") --output "$(KG_DIR)" $(if $(KG_PAPERS),--papers "$(KG_PAPERS)",)

kg-extract:
	uv run --group kg python -m src.api.kg extract --output "$(KG_DIR)" $(if $(KG_MAX_CALLS),--max-calls "$(KG_MAX_CALLS)",) $(if $(filter true,$(KG_RETRY_FAILED)),--retry-failed,) $(if $(filter true,$(KG_FAILED_ONLY)),--failed-only,) $(if $(KG_CHUNKS_PER_PAPER),--chunks-per-paper "$(KG_CHUNKS_PER_PAPER)",)

kg-validate:
	uv run --group kg python -m src.api.kg validate --output "$(KG_DIR)"

kg-review-prepare:
	uv run --group kg python -m src.api.kg review-prepare --output "$(KG_DIR)" --review "$(KG_REVIEW)"

kg-review-set:
	uv run --group kg python -m src.api.kg review-set --output "$(KG_DIR)" --review "$(KG_REVIEW)" --record-id "$(KG_RECORD_ID)" --decision "$(KG_DECISION)" --reviewer "$(KG_REVIEWER)" $(if $(KG_REASON),--reason "$(KG_REASON)",) $(if $(KG_NOTES),--notes "$(KG_NOTES)",)

kg-review-validate:
	uv run --group kg python -m src.api.kg review-validate --output "$(KG_DIR)" --review "$(KG_REVIEW)"

kg-review-export:
	uv run --group kg python -m src.api.kg review-export --output "$(KG_DIR)" --review "$(KG_REVIEW)"

kg-publish-preview:
	uv run --group kg python -m src.api.kg publish-preview --output "$(KG_DIR)" --review "$(KG_REVIEW)" $(if $(KG_GRAPH),--graph-name "$(KG_GRAPH)",)

kg-publish:
	uv run --group kg python -m src.api.kg publish --output "$(KG_DIR)" --review "$(KG_REVIEW)" $(if $(KG_GRAPH),--graph-name "$(KG_GRAPH)",)

kg-publication-verify:
	uv run --group kg python -m src.api.kg publication-verify --output "$(KG_DIR)" --review "$(KG_REVIEW)" $(if $(KG_GRAPH),--graph-name "$(KG_GRAPH)",)

kg-activate:
	uv run --group kg python -m src.api.kg activate --output "$(KG_DIR)" --review "$(KG_REVIEW)" --expect-active "$(KG_EXPECT_ACTIVE)" $(if $(KG_GRAPH),--graph-name "$(KG_GRAPH)",)

kg-publication-status:
	uv run --group kg python -m src.api.kg publication-status $(if $(KG_GRAPH),--graph-name "$(KG_GRAPH)",)

kg-test:
	LANGFUSE_ENABLED=false uv run --group kg python -m pytest tests/unit/test_kg_foundation.py tests/unit/test_kg_extraction.py tests/unit/test_kg_selection.py tests/unit/test_kg_spans.py tests/unit/test_kg_scientific_schema.py tests/unit/test_kg_review.py tests/unit/test_kg_publication.py tests/unit/test_kg_retrieval.py tests/unit/test_kg_runtime.py tests/unit/test_kg_catalogue.py -q

kg-test-neo4j:
	KG_RUN_NEO4J_INTEGRATION=1 LANGFUSE_ENABLED=false uv run --group kg python -m pytest tests/integration/test_kg_neo4j_publication.py -q

kg-help:
	@printf '%s\n' \
	  'KG workflow (KG query mode is available; KG-Agentic remains planned):' \
	  '  make kg-catalogue KG_TERM=M22    Browse live ready metadata; paged, no model calls' \
	  '  make kg-select KG_DIR=... KG_PAPER_IDS="id1 id2"  Freeze explicit IDs, including original pilot by default' \
	  '  make kg-prepare-preview KG_DIR=... KG_CHUNKS_PER_PAPER=3  Verify artifacts and preview call counts; no writes' \
	  '  make kg-prepare KG_DIR=... KG_SELECTION_FILE=.../selection.json  Prepare selected live builds, independent of evaluation' \
	  '  make kg-preview                  Preview seven connected papers; no calls/writes' \
	  '  make kg-preview KG_SELECTION=all Preview every paper in the saved snapshot' \
	  '  make kg-schema                   Show the typed extraction schema' \
	  '  make kg-prepare KG_PAPERS=1       Verify/freeze one full paper; no model calls' \
	  '  make kg-extract KG_MAX_CALLS=5    PAID: extract at most five pending chunks' \
	  '  make kg-extract KG_CHUNKS_PER_PAPER=3 KG_MAX_CALLS=21  PAID: distributed paper sample' \
	  '  make kg-extract KG_FAILED_ONLY=true KG_MAX_CALLS=4    PAID: retry only failed/interrupted chunks' \
	  '  make kg-validate                 Validate checkpoints; scientific review still needed' \
	  '  make kg-review-prepare           Create a separate review.json; no approvals inferred' \
	  '  make kg-review-set KG_RECORD_ID=... KG_DECISION=excluded KG_REASON=presentation_only KG_REVIEWER=... ' \
	  '  make kg-review-validate          Check attributed decisions and dependency eligibility' \
	  '  make kg-review-export            Export approved-only local projection; no Neo4j writes' \
	  '  make kg-publish-preview          Check approved subset and active SQL/artifact scope; no graph writes' \
	  '  make kg-publish                  Stage an immutable approved-only Neo4j publication' \
	  '  make kg-publication-verify       Audit exact graph content/provenance and current SQL scope' \
	  '  make kg-activate                 Explicit first activation; replacement needs KG_EXPECT_ACTIVE=...' \
	  '  make kg-publication-status       Inspect Neo4j pointer/history; not a PostgreSQL eligibility check' \
	  '  make kg-test                     Offline tests, with mocked provider responses' \
	  '  make kg-test-neo4j               Native tests in a disposable Neo4j container; no .env/Compose' \
	  '  make kg-up                       Start optional Neo4j; UI: http://localhost:7474' \
	  '  make kg-status / kg-logs          Inspect the graph database service' \
	  '  make kg-password                 Show local Neo4j login credentials and Browser URL (sensitive output)' \
	  '  make kg-stop                     Stop Neo4j; preserve its data volumes' \
	  'KG_SNAPSHOT and KG_PILOT accept alternate local files.' \
	  'Guide: docs/architecture/knowledge-graph.md'

# Paper catalogue, ingestion and backup commands.
BACKUP_DIR ?= $(HOME)/rag-demo-backups
.PHONY: papers-help papers-scope papers-preview papers-db-up papers-init-db \
        papers-backfill papers-process papers-sync papers-daily papers-status papers-count papers-audit papers-import-uploads \
        papers-backup papers-backups papers-backup-check
# Export paths as values, never interpolate user paths into shell commands.
papers-backup papers-backups papers-backup-check: export PAPERS_BACKUP_DIR := $(BACKUP_DIR)
papers-backup-check: export PAPERS_BACKUP_FILE := $(FILE)

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
	  '  make papers-extractor-setup          Prepare tokenizer cache; no model calls' \
	  '  make papers-extract-preview PDF=...  Inspect local Markdown/chunks; no embeddings' \
	  '  make papers-reindex-preview          List existing arXiv papers needing extraction upgrade' \
	  '  make papers-reindex LIMIT=2          Upgrade existing arXiv papers (paid embeddings)' \
	  '  make papers-audit                    Read-only SQL/Qdrant consistency audit' \
	  '  make papers-import-uploads LEGACY_MODEL=text-embedding-3-small' \
	  '                                       Register existing upload vectors in SQL; no re-embedding' \
	  '  make papers-process LIMIT=2          Download/index pending PDFs (paid embeddings)' \
	  '  make papers-sync                     Discover metadata updates only' \
	  '  make papers-daily LIMIT=10           Sync + process once (paid embeddings)' \
	  '  make papers-scheduled LIMIT=10       Durable daily budget + audit + notifications (paid)' \
	  '  make papers-run-status              Read saved daily run summary/state' \
	  '  make airflow-up                     Start optional Airflow; new DAG is paused' \
	  '  make airflow-password               Show the generated local Airflow login credentials' \
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

papers-backup:
	python3 scripts/papers_backup.py backup

papers-backups:
	python3 scripts/papers_backup.py list

papers-backup-check:
	python3 scripts/papers_backup.py check

papers-init-db:
	$(PAPERS_CLI) init-db

papers-backfill:
	$(PAPERS_CLI) backfill $(PAPERS_BACKFILL_ARGS)

# Explicit opt-in to PDF downloads and embedding API usage.
papers-process:
	$(PAPERS_CLI) process $(PAPERS_PROCESS_ARGS)

.PHONY: papers-reindex-preview papers-reindex papers-extractor-setup papers-extract-preview
papers-extractor-setup:
	uv run python -c 'from src.api.papers.extraction import encoder; encoder(); print("Tokenizer cache ready (no model calls)")'

EXTRACT_DIR ?= data/extraction-preview
papers-extract-preview:
	uv run python -m src.api.papers.extraction --pdf "$(PDF)" --output "$(EXTRACT_DIR)"

papers-reindex-preview:
	$(PAPERS_CLI) reindex --dry-run

# Explicit paid upgrade of existing active arXiv papers only (not discovery backlog).
papers-reindex:
	$(PAPERS_CLI) reindex $(PAPERS_PROCESS_ARGS)

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
EVAL_REASONING_EFFORT ?=
EVAL_MAX_TOKENS ?= 2500
EVAL_SINGLE_FACT ?=
EVAL_SINGLE_SYNTHESIS ?=
EVAL_CROSS_COMPARISON ?=
EVAL_CROSS_MULTIHOP ?=
EVAL_METADATA_DISCOVERY ?=
EVAL_UNANSWERABLE ?=
EVAL_SOURCE ?= arxiv
QUESTIONS ?= 50
PAPERS ?= 50
EVAL_SEED ?= 42
EVAL_REVIEWED ?= $(EVAL_DIR)/questions.reviewed.json
EVAL_RUNS_DIR ?= data/evaluation/runs
EVAL_MODES ?= vanilla hybrid hybrid_rerank agentic
EVAL_KG_PUBLICATION_ID ?=
EVAL_TOP_K ?= 5
EVAL_LIMIT ?=
EVAL_QUESTION_ID ?=
EVAL_PROFILES ?=
EVAL_GENERATION_MODEL ?=
# Optional per-run Agentic draft/repair override; empty preserves Config/.env.
EVAL_DRAFT_REASONING_EFFORT ?=
EVAL_JUDGE ?= false
EVAL_JUDGE_MODEL ?= gpt-5-mini
EVAL_JUDGE_REASONING_EFFORT ?= minimal
EVAL_CONCURRENCY ?= 1
EVAL_SPLIT ?= all
EVAL_SPLIT_OUTPUT ?= $(EVAL_DIR)/questions.split.json
EVAL_TEST_RATIO ?= 0.25
EVAL_FROM ?=

.PHONY: eval-preview eval-check create-eval-dataset eval-rebase eval-validate eval-split eval-run

# Freeze active paper evidence locally. No model calls or database writes.
eval-preview:
	uv run python -m evals.generate_questions prepare --output "$(EVAL_DIR)" --source "$(EVAL_SOURCE)" --questions "$(QUESTIONS)" --papers "$(PAPERS)" --seed "$(EVAL_SEED)" --model "$(EVAL_MODEL)" $(if $(EVAL_REASONING_EFFORT),--reasoning-effort "$(EVAL_REASONING_EFFORT)") --max-completion-tokens "$(EVAL_MAX_TOKENS)" $(if $(EVAL_SINGLE_FACT),--single-fact "$(EVAL_SINGLE_FACT)") $(if $(EVAL_SINGLE_SYNTHESIS),--single-synthesis "$(EVAL_SINGLE_SYNTHESIS)") $(if $(EVAL_CROSS_COMPARISON),--cross-comparison "$(EVAL_CROSS_COMPARISON)") $(if $(EVAL_CROSS_MULTIHOP),--cross-multihop "$(EVAL_CROSS_MULTIHOP)") $(if $(EVAL_METADATA_DISCOVERY),--metadata-discovery "$(EVAL_METADATA_DISCOVERY)") $(if $(EVAL_UNANSWERABLE),--unanswerable "$(EVAL_UNANSWERABLE)")

# Explicit paid generation; resumes completed calls and writes local drafts.
create-eval-dataset:
	uv run python -m evals.generate_questions generate --output "$(EVAL_DIR)" $(if $(EVAL_WAIT_SECONDS),--wait-seconds "$(EVAL_WAIT_SECONDS)") $(if $(RETRY_JOB),--retry-job "$(RETRY_JOB)")

# Read-only model metadata request; no inference or changes to saved evaluation data.
eval-check:
	uv run python -m evals.generate_questions check --output "$(EVAL_DIR)"

# Reuse reviewed questions on the current dense+sparse corpus; no model calls or writes.
eval-rebase:
	uv run python -m evals.rebase_dataset --dataset "$(EVAL_FROM)" --output "$(EVAL_DIR)"

# Validate the local reviewed dataset and its frozen snapshot; no service calls.
eval-validate:
	uv run python -m evals.review_dataset validate --dataset "$(EVAL_REVIEWED)" --split "$(EVAL_SPLIT)"

# Write a new schema-v2 reviewed file with paper-component development/test splits.
eval-split:
	uv run python -m evals.review_dataset assign-splits --dataset "$(EVAL_REVIEWED)" --output "$(EVAL_SPLIT_OUTPUT)" --test-ratio "$(EVAL_TEST_RATIO)" --seed "$(EVAL_SEED)"

# Run the reviewed benchmark against one or more explicit retrieval modes.
# This performs paid embedding/generation calls; EVAL_JUDGE=true adds a paid judge call.
eval-run:
	$(if $(EVAL_DRAFT_REASONING_EFFORT),AGENT_DRAFT_REASONING_EFFORT="$(EVAL_DRAFT_REASONING_EFFORT)" )uv run python -m evals.run_benchmark --dataset "$(EVAL_REVIEWED)" --output-root "$(EVAL_RUNS_DIR)" --modes $(EVAL_MODES) --split "$(EVAL_SPLIT)" --top-k "$(EVAL_TOP_K)" $(if $(EVAL_GENERATION_MODEL),--generation-model "$(EVAL_GENERATION_MODEL)") $(if $(filter true 1 yes,$(EVAL_JUDGE)),--judge,--no-judge) --judge-model "$(EVAL_JUDGE_MODEL)" --judge-reasoning-effort "$(EVAL_JUDGE_REASONING_EFFORT)" --concurrency "$(EVAL_CONCURRENCY)" $(if $(EVAL_PROFILES),--profiles $(EVAL_PROFILES)) $(if $(EVAL_QUESTION_ID),--question-id "$(EVAL_QUESTION_ID)") $(if $(EVAL_LIMIT),--limit "$(EVAL_LIMIT)") $(if $(EVAL_KG_PUBLICATION_ID),--kg-publication-id "$(EVAL_KG_PUBLICATION_ID)")

.PHONY: build run docs docs-build docs-deploy

# Frontend
.PHONY: ui-update ui-build ui-run ui-tag ui-push update-ui streamlit-update build-ui run-ui tag-ui push-ui

# Compatibility aliases; prefer the grouped ui-* names for new commands.
update-ui streamlit-update: ui-update
build-ui: ui-build
run-ui: ui-run
tag-ui: ui-tag
push-ui: ui-push

# Update only the Compose UI; the API must already be running (e.g. make compose).
ui-update:
	@set -e
	docker compose up -d --build --no-deps --force-recreate --wait streamlit-app
	echo "Streamlit updated: http://localhost:8501"

ui-build:
	@echo "Building image version: $(VERSION)"
	@docker build -t $(FRONTEND_IMAGE_NAME):$(VERSION)  -f Dockerfile.streamlit .
	@echo "Built image: $(FRONTEND_IMAGE_NAME):$(VERSION)"

ui-run:
	@echo "Running image version: $(VERSION)"
	@docker run -d -p 8501:8501 --env-file .env --name $(FRONTEND_IMAGE_NAME) $(FRONTEND_IMAGE_NAME):$(VERSION)
	@echo "Running image: $(FRONTEND_IMAGE_NAME):$(VERSION)"
	@echo "Access the app at http://localhost:8501"

ui-tag:
	@echo "Tag image version: $(VERSION)"
	@docker tag $(FRONTEND_IMAGE_NAME):$(VERSION) $(DOCKER_FOLDER)/$(FRONTEND_IMAGE_NAME):$(VERSION)
	@echo "Tagged image: $(DOCKER_FOLDER)/$(FRONTEND_IMAGE_NAME):$(VERSION)"

ui-push:
	@echo "Pushing image version: $(VERSION)"
	@docker push $(DOCKER_FOLDER)/$(FRONTEND_IMAGE_NAME):$(VERSION)
	@echo "Pushed image: $(DOCKER_FOLDER)/$(FRONTEND_IMAGE_NAME):$(VERSION)"		


# Backend
.PHONY: fastapi-build fastapi-run fastapi-tag fastapi-push build-fastapi run-fastapi tag-fastapi push-fastapi

# Compatibility aliases; prefer the grouped fastapi-* names for new commands.
build-fastapi: fastapi-build
run-fastapi: fastapi-run
tag-fastapi: fastapi-tag
push-fastapi: fastapi-push

fastapi-build:
	@echo "Building image version: $(VERSION)"
	@docker build -t $(BACKEND_IMAGE_NAME):$(VERSION) -f Dockerfile.fastapi .
	@echo "Built image: $(BACKEND_IMAGE_NAME):$(VERSION)"

fastapi-run:
	@echo "Running image version: $(VERSION)"
	@docker run -d -p 8000:8000 --env-file .env --name $(BACKEND_IMAGE_NAME) $(BACKEND_IMAGE_NAME):$(VERSION)
	@echo "Running image: $(BACKEND_IMAGE_NAME):$(VERSION)"
	@echo "Access the app at http://localhost:8000"

fastapi-tag:
	@echo "Tag image version: $(VERSION)"
	@docker tag $(BACKEND_IMAGE_NAME):$(VERSION) $(DOCKER_FOLDER)/$(BACKEND_IMAGE_NAME):$(VERSION)
	@echo "Tagged image: $(DOCKER_FOLDER)/$(BACKEND_IMAGE_NAME):$(VERSION)"

fastapi-push:
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
