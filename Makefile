.DEFAULT_GOAL := help

.PHONY: help setup dev web api test lint format typecheck build docker seed knowledge eval verify worker ingest infra-plan infra-apply deploy

eval: ## Run deterministic agent evaluation and regression gates
	UV_CACHE_DIR=$${UV_CACHE_DIR:-/tmp/geoops-ai-uv-cache} uv run --package geoops-api python -m geoops_api.evaluation --local

verify: ## Exercise the live web proxy, approval, dispatch, and evaluation path
	uv run --package geoops-api python scripts/verify_local.py

worker: ## Run the local Pub/Sub push receiver on port 8001
	uv run --package geoops-api uvicorn geoops_api.worker_app:app --host 127.0.0.1 --port 8001

ingest: ## Ingest documents through the configured storage and vector providers
	uv run --package geoops-api python -m geoops_api.ingestion

infra-plan: ## Preview configured cloud infrastructure changes
	terraform -chdir=infrastructure/terraform init
	terraform -chdir=infrastructure/terraform plan

infra-apply: ## Apply a reviewed infrastructure plan interactively
	terraform -chdir=infrastructure/terraform apply

deploy: ## Submit the configured Cloud Build deployment pipeline
	gcloud builds submit --config=cloudbuild.yaml --substitutions=_DEPLOY=true

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*##"; printf "GeoOps AI commands:\n"} /^[a-zA-Z_-]+:.*?##/ {printf "  %-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Install JavaScript and Python dependencies
	pnpm install
	UV_CACHE_DIR=$${UV_CACHE_DIR:-/tmp/geoops-ai-uv-cache} uv sync --all-packages

dev: ## Run the API and web app together with hot reload
	pnpm dev

web: ## Run the Next.js development server
	pnpm web

api: ## Run the FastAPI development server
	pnpm api

seed: ## Regenerate the deterministic local dataset
	UV_CACHE_DIR=$${UV_CACHE_DIR:-/tmp/geoops-ai-uv-cache} uv run --package geoops-api python -m geoops_api.seed

knowledge: ## Validate and index local knowledge documents
	UV_CACHE_DIR=$${UV_CACHE_DIR:-/tmp/geoops-ai-uv-cache} uv run --package geoops-api python -m geoops_api.knowledge.ingest

test: ## Run all unit tests
	pnpm test

lint: ## Lint TypeScript and Python
	pnpm lint

format: ## Format TypeScript and Python
	pnpm format

typecheck: ## Type-check TypeScript and Python
	pnpm typecheck

build: ## Build the web app and Python package
	pnpm build

docker: ## Build and start the local Docker Compose stack
	docker compose up --build
