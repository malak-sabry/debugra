VENV_PYTHON := .venv/Scripts/python  # Windows; Linux/macOS: .venv/bin/python
VENV_PY     := $(shell [ -f .venv/bin/python ] && echo .venv/bin/python || echo .venv/Scripts/python)

.PHONY: help setup dev demo lint test clean

help:
	@echo "Debugra — Autonomous AI QA System"
	@echo ""
	@echo "  make setup       Install all dependencies"
	@echo "  make dev         Start orchestrator + dashboard in dev mode"
	@echo "  make demo        Full demo: LMS + Shop SUTs + Debugra stack"
	@echo "  make demo-lms    Start only LMS SUT + Debugra"
	@echo "  make demo-shop   Start only Shop SUT + Debugra"
	@echo "  make lint        Run ruff + eslint"
	@echo "  make test        Run pytest + vitest"
	@echo "  make clean       Remove run artifacts"

setup:
	cp -n .env.example .env || true
	pnpm install
	uv sync --all-packages
	$(VENV_PY) -m playwright install chromium

dev:
	docker compose -f infra/docker-compose.debugra.yml up -d db redis
	pnpm --filter dashboard dev &
	cd apps/orchestrator && $(VENV_PY) -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

demo:
	docker compose -f infra/docker-compose.lms.yml up -d
	docker compose -f infra/docker-compose.shop.yml up -d
	docker compose -f infra/docker-compose.debugra.yml up -d
	@echo "Dashboard → http://localhost:3000"
	@echo "Orchestrator → http://localhost:8000/docs"

demo-lms:
	docker compose -f infra/docker-compose.lms.yml up -d
	docker compose -f infra/docker-compose.debugra.yml up -d

demo-shop:
	docker compose -f infra/docker-compose.shop.yml up -d
	docker compose -f infra/docker-compose.debugra.yml up -d

lint:
	$(VENV_PY) -m ruff check apps/orchestrator apps/agent-runner packages/schemas suts
	pnpm --recursive lint

test:
	$(VENV_PY) -m pytest apps/orchestrator/tests apps/agent-runner/tests -v
	pnpm --filter dashboard test

clean:
	rm -rf runs/
	docker compose -f infra/docker-compose.lms.yml down -v
	docker compose -f infra/docker-compose.shop.yml down -v
	docker compose -f infra/docker-compose.debugra.yml down -v
