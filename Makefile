.DEFAULT_GOAL := help

.PHONY: help setup dev web api test lint format typecheck build docker

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

