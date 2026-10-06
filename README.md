# GeoOps AI

GeoOps AI is a geospatial AI operations platform for field-service teams. The planned system combines structured operational data, geospatial reasoning, enterprise knowledge retrieval, typed agent tools, human approval, asynchronous dispatch, and reproducible evaluation.

This repository currently contains **Phase 1 only**: a tested Next.js operations shell connected to a tested FastAPI gateway. It intentionally does not include placeholder business data or simulated performance metrics.

## Current capabilities

- Responsive and accessible operations console
- Live browser-to-API health verification with loading, error, retry, and success states
- Typed, deterministic `GET /health` API contract and generated OpenAPI documentation
- Validated environment configuration with safe local defaults
- Configurable CORS for local browser access
- Correlation IDs and structured JSON request logs
- pnpm and uv workspaces with committed lockfiles
- Unit tests, linting, strict type checking, and production builds
- Development and production container targets

## Architecture

```mermaid
flowchart LR
    USER[Operations user]
    WEB[Next.js console<br/>localhost:3000]
    API[FastAPI gateway<br/>localhost:8000]
    LOGS[Structured JSON logs]

    USER --> WEB
    WEB -->|GET /health| API
    API --> LOGS

    FUTURE[Phase 2+ services]
    API -. typed boundaries .-> FUTURE
```

The browser calls the API directly so Phase 1 exercises the real cross-origin application boundary. The API owns runtime configuration and returns a stable schema. Future data, agent, and cloud adapters will sit behind the API instead of leaking infrastructure concerns into the UI.

## Repository layout

```text
.
├── apps/
│   ├── api/              # FastAPI package, tests, and container
│   └── web/              # Next.js application, tests, and container
├── .env.example          # Canonical local configuration contract
├── docker-compose.yml    # Hot-reloading local container stack
├── Makefile              # Developer workflow
├── package.json          # pnpm orchestration scripts
├── pnpm-workspace.yaml
└── pyproject.toml        # uv workspace and Python tooling
```

Directories for workers, domain packages, data, and infrastructure will be introduced only when their implementation phase begins.

## Prerequisites

- Node.js 22 or newer; Node 24 LTS is the container baseline
- pnpm 10.29.3
- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- GNU Make or a compatible `make`
- Docker with Compose v2 only if using the container workflow

## Local setup

```bash
cp .env.example .env
make setup
make dev
```

Open:

- Web console: <http://localhost:3000>
- API health: <http://localhost:8000/health>
- OpenAPI documentation: <http://localhost:8000/docs>

`make dev` runs both applications with hot reload. Use `Ctrl+C` once to stop both processes.

If `make` is unavailable, run the underlying cross-platform commands directly:

```bash
pnpm install
uv sync --all-packages
pnpm dev
```

Run either application independently with:

```bash
make web
make api
```

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | API environment label returned by `/health` |
| `LOG_LEVEL` | `INFO` | Python structured-log threshold |
| `CORS_ORIGINS` | Local web origins | JSON array of allowed browser origins |
| `HOST` | `0.0.0.0` | API bind host for local tooling and containers |
| `PORT` | `8000` | API port |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Browser-visible API origin |

Values prefixed with `NEXT_PUBLIC_` are embedded in browser assets and must never contain secrets.

## Quality checks

```bash
make lint
make typecheck
make test
make build
```

To format supported source files:

```bash
make format
```

The API test suite covers its public contract, environment overrides, CORS preflight, supplied and generated correlation IDs, and unknown routes. The web suite covers loading, healthy, unavailable, and retry states.

## Containers

Start the hot-reloading Compose stack:

```bash
make docker
```

Build production targets directly:

```bash
docker build -f apps/api/Dockerfile --target production -t geoops-api:local .
docker build -f apps/web/Dockerfile --target production -t geoops-web:local .
```

Both production images run as non-root users and include health checks. The web build defaults to `http://localhost:8000` for its browser-visible API URL; override `NEXT_PUBLIC_API_BASE_URL` as a build argument for deployed environments.

## HTTP contract

`GET /health` returns HTTP 200 while the API process is healthy:

```json
{
  "status": "ok",
  "service": "geoops-api",
  "environment": "development",
  "version": "0.1.0"
}
```

Every response includes `X-Request-ID`. A caller-supplied ID is propagated; otherwise the API generates one. Request telemetry is emitted as structured JSON without credentials or request bodies.

## Engineering decisions

- **pnpm + uv:** fast, deterministic, language-appropriate workspaces without hiding commands behind a custom task runner.
- **Direct health call:** verifies the browser/API boundary and CORS behavior rather than masking it behind a Next.js proxy.
- **Application factory:** FastAPI construction accepts explicit settings, keeping tests deterministic and future dependency injection straightforward.
- **No empty architecture:** services and cloud resources arrive in the phase that needs them, avoiding unused abstractions.
- **No fake dashboard metrics:** the console reports only live service state until Phase 2 provides real operational records.
- **Local-only Phase 1:** no cloud project, credentials, model key, or hosted deployment is required.

## Roadmap

1. **Foundation — complete here:** web, API, configuration, tests, containers, local workflow.
2. **Domain and data:** typed entities, repository boundaries, deterministic seed data, ticket and technician browsing.
3. **Deterministic dispatch:** eligibility rules and explainable candidate scoring.
4. **Maps:** mock and Google Maps provider adapters with route matrices.
5. **Knowledge retrieval:** ingestion, chunking, embeddings, BigQuery vector search, citations.
6. **Agent orchestration:** typed tools and provider-neutral Gemini/ADK integration.
7. **Human approval:** explicit mutation proposals and approval state machine.
8. **Async dispatch:** event bus, idempotent worker, and operational updates.
9. **Evaluation:** reproducible datasets, quality metrics, and regression gates.
10. **Observability, infrastructure, and CI/CD:** cloud telemetry, Terraform, and deployment automation.
