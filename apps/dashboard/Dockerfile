# Build from monorepo root: docker build -f apps/dashboard/Dockerfile .
# ── builder ───────────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app
RUN npm install -g pnpm@9.14.4

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* ./
COPY apps/dashboard/package.json ./apps/dashboard/
COPY packages/schemas/package.json ./packages/schemas/
RUN pnpm install --frozen-lockfile || pnpm install

COPY packages/schemas ./packages/schemas
COPY apps/dashboard ./apps/dashboard

ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG ORCHESTRATOR_INTERNAL_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV ORCHESTRATOR_INTERNAL_URL=$ORCHESTRATOR_INTERNAL_URL

WORKDIR /app/apps/dashboard
RUN pnpm build

# ── runner ────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs && \
    adduser  --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/apps/dashboard/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/dashboard/.next/static ./apps/dashboard/.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000 HOSTNAME=0.0.0.0
CMD ["node", "apps/dashboard/server.js"]
