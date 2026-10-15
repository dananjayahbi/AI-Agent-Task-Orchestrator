# syntax=docker/dockerfile:1
#
# Real Next.js operations-board image — the "WP-4.1 replaces with the real
# image" wiring promised by infra/compose/.env.example (parent plan Section
# 16.1; local-first hosting decision 2026-10-15). Deliberately one stage:
# `next start` evaluates next.config.ts (the /api/v1 rewrites) at runtime and
# loads the project's TypeScript toolchain, so the build toolchain stays in
# the image. The container-build CI gate discovers this Dockerfile by pattern
# (MT-0.3-03) and builds it on every PR — no workflow edits needed.

FROM node:24-alpine

WORKDIR /app

# Dependencies first, layer-cached: full install (not --omit=dev) — next
# build needs the dev toolchain (typescript, postcss/tailwind) and next start
# loads next.config.ts from this same tree.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

# Server-side API rewrite target (next.config.ts reads this at RUNTIME): the
# compose-internal service name on the internal network — never the
# host-published port (Section 16.1 internal DNS). The browser only ever
# talks same-origin `/api/v1/*`, which this server rewrites upstream.
ENV ORCHESTRATOR_API_BASE_URL=http://backend:8000/api/v1
ENV NODE_ENV=production

RUN npm run build

# Compose healthcheck probes http://127.0.0.1:3000/ inside this container
# (busybox wget exists in alpine); the published host port comes from
# ORCHESTRATOR_PORT_WEB.
EXPOSE 3000
CMD ["npm", "run", "start"]
