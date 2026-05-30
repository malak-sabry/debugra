from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orchestrator.api.routes import artifacts as artifacts_router
from orchestrator.api.routes import runs as runs_router
from orchestrator.api.routes import ws as ws_router
from orchestrator.config import get_settings
from orchestrator.db import create_tables

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(
    title="Debugra Orchestrator",
    version="0.1.0",
    description="Autonomous AI QA system — central orchestration API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs_router.router, prefix="/api")
app.include_router(artifacts_router.router, prefix="/api")
app.include_router(ws_router.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "orchestrator"}
