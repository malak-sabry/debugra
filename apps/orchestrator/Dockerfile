FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates fonts-liberation libnss3 libatk-bridge2.0-0 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libasound2 libpango-1.0-0 libpangocairo-1.0-0 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

COPY packages/schemas /app/packages/schemas
COPY apps/orchestrator /app/apps/orchestrator
COPY apps/agent-runner /app/apps/agent-runner
COPY packages/prompts /app/packages/prompts
COPY pyproject.toml /app/pyproject.toml

RUN pip install uv && \
    uv sync --package orchestrator --package agent-runner --package debugra-schemas

ENV PYTHONPATH=/app:/app/apps/orchestrator:/app/apps/agent-runner
ENV PLAYWRIGHT_HEADLESS=true

RUN uv run playwright install chromium

WORKDIR /app/apps/orchestrator
EXPOSE 8000

CMD ["/app/.venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
