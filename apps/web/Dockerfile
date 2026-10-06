# syntax=docker/dockerfile:1.7

FROM node:24-alpine AS base

ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
RUN corepack enable && corepack prepare pnpm@10.29.3 --activate
WORKDIR /workspace

FROM base AS dependencies

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/
RUN pnpm install --frozen-lockfile --filter @geoops/web...

FROM dependencies AS development

COPY apps/web ./apps/web
EXPOSE 3000
CMD ["pnpm", "--filter", "@geoops/web", "dev"]

FROM dependencies AS builder

ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_TELEMETRY_DISABLED=1

COPY apps/web ./apps/web
RUN pnpm --filter @geoops/web build

FROM node:24-alpine AS production

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

WORKDIR /app
RUN addgroup --system --gid 10001 geoops \
    && adduser --system --uid 10001 --ingroup geoops geoops

COPY --from=builder --chown=geoops:geoops /workspace/apps/web/.next/standalone ./
COPY --from=builder --chown=geoops:geoops /workspace/apps/web/.next/static ./apps/web/.next/static

USER geoops
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["wget", "--no-verbose", "--tries=1", "--spider", "http://127.0.0.1:3000/"]

CMD ["node", "apps/web/server.js"]

