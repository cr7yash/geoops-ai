# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.11.3 AS uv

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app
COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/README.md ./apps/api/

RUN uv sync --frozen --no-dev --no-install-workspace --package geoops-api

FROM base AS development

RUN uv sync --frozen --all-groups --no-install-workspace --package geoops-api
COPY apps/api/src ./apps/api/src
COPY apps/api/tests ./apps/api/tests
COPY data/seed ./data/seed
RUN uv sync --frozen --all-groups --package geoops-api

EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "geoops_api.main:app", "--app-dir", "apps/api/src", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production-builder

COPY apps/api/src ./apps/api/src
COPY data/seed ./data/seed
RUN uv sync --frozen --no-dev --package geoops-api

FROM python:3.13-slim AS production

ENV PATH=/app/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY --from=production-builder /app/.venv /app/.venv
COPY --from=production-builder /app/apps/api/src /app/apps/api/src
COPY --from=production-builder /app/data/seed /app/data/seed

RUN addgroup --system --gid 10001 geoops \
    && adduser --system --uid 10001 --ingroup geoops geoops

USER geoops
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

CMD ["uvicorn", "geoops_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
