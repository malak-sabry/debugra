# Debugra

> Autonomous AI Software Validation — competition prototype

Debugra autonomously reads a project's documentation, understands its roles and workflows, launches multi-agent browser sessions, explores the application like a human tester, detects bugs, and generates professional QA reports.

## Quick Start

```bash
# 1. Copy env and install dependencies
make setup

# 2. Start infrastructure (Postgres + Redis)
docker compose -f infra/docker-compose.debugra.yml up -d db redis

# 3. Start orchestrator + dashboard (dev mode)
make dev

# 4. Full demo (both SUTs + Debugra)
make demo
```

Open http://localhost:3000 to access the dashboard.

## Architecture

```
Dashboard (Next.js) ←WS→ Orchestrator (FastAPI + LangGraph) → Agent Workers (Playwright)
                                   ↓                                    ↓
                             Postgres + Redis                     SUT Containers
```

See [docs/architecture.md](docs/architecture.md) for the full system design.

## Repository Layout

```
apps/
  dashboard/        Next.js 15 — live tiles, logs, findings, replay
  orchestrator/     FastAPI + LangGraph — central brain
  agent-runner/     Playwright workers — observe→think→act loop
packages/
  schemas/          Shared Pydantic + TypeScript types
  prompts/          Versioned LLM prompt files
suts/
  lms/              School LMS (10 seeded bugs)
  shop/             E-commerce Checkout (8 seeded bugs)
infra/              Docker Compose files
benchmark/          Human-vs-AI study protocol + bug catalog
docs/               Architecture, demo script, paper draft
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | Python 3.12, FastAPI, LangGraph |
| Browser agents | Playwright (Python async) |
| LLM — planning/reports | Claude Sonnet 4.5 (Anthropic) |
| LLM — action selection | Llama 3.1 8B via Ollama (local) |
| Dashboard | Next.js 15, Tailwind CSS, shadcn/ui |
| Database | PostgreSQL 16, Redis 7 |
| Packaging | pnpm workspaces (JS), uv workspaces (Python) |
| Containers | Docker + Docker Compose |
