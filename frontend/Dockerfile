# Cloud AI Trader — Frontend (Next.js), 3-stage build for a lean runtime image.
#
# BACKEND_URL must be a BUILD ARG, not a runtime environment variable —
# verified live 2026-07-26: next.config.mjs's rewrites() is evaluated by
# `next build` and frozen into the generated routing manifest, NOT
# re-evaluated when the standalone server boots. Setting it only via
# docker-compose's `environment:` (runtime) silently had no effect — the
# proxy kept trying the http://localhost:8000 default baked in at build
# time, logging "Failed to proxy ... ECONNREFUSED" even though the backend
# container was reachable by name (confirmed with a manual wget from inside
# the frontend container). Passing it as an ARG here, and as a compose
# `build.args` entry, is what actually reaches rewrites().

FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:24-alpine AS builder
WORKDIR /app
ARG BACKEND_URL=http://localhost:8000
ENV BACKEND_URL=$BACKEND_URL
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
# Docker auto-sets HOSTNAME to the container ID, and Next.js's standalone
# server.js does `process.env.HOSTNAME || '0.0.0.0'` — since HOSTNAME is
# already set, it binds to that container-ID hostname specifically instead
# of all interfaces, so `localhost` (used by the HEALTHCHECK below, and by
# anything else reaching it from outside the container) can't connect.
# Verified live 2026-07-26: HOSTNAME=<container-id>, server logged "Ready"
# but wget --spider http://localhost:3000/ got connection refused. Explicit
# override forces the intended bind-all behavior.
ENV HOSTNAME="0.0.0.0"
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

# 127.0.0.1, not localhost — Alpine/musl's getaddrinfo resolves "localhost"
# to IPv6 ::1 first (verified via /etc/hosts + netstat), but the Next.js
# server only binds IPv4 0.0.0.0, so "localhost" got connection refused
# while the server was demonstrably up and Ready.
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD wget --spider -q http://127.0.0.1:3000/ || exit 1

CMD ["node", "server.js"]
