from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from orchestrator.config import get_settings
from debugra_schemas import RunStatus, AgentStatus, AgentRole, Severity, SUT, ActionTool

settings = get_settings()


engine = create_async_engine(settings.database_url, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session


class Base(DeclarativeBase):
    pass


class RunModel(Base):
    __tablename__ = "runs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    sut: Mapped[str] = mapped_column(Enum(SUT), nullable=False)
    status: Mapped[str] = mapped_column(Enum(RunStatus), default=RunStatus.PENDING)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    plan: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    artifact_dir: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    agents: Mapped[list[AgentModel]] = relationship("AgentModel", back_populates="run")
    findings: Mapped[list[FindingModel]] = relationship("FindingModel", back_populates="run")


class AgentModel(Base):
    __tablename__ = "agents"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    run_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("runs.id"))
    role: Mapped[str] = mapped_column(Enum(AgentRole), nullable=False)
    status: Mapped[str] = mapped_column(Enum(AgentStatus), default=AgentStatus.PENDING)
    model: Mapped[str] = mapped_column(String(128), default="ollama/llama3.1:8b")
    step_count: Mapped[int] = mapped_column(Integer, default=0)
    trace_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    video_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    run: Mapped[RunModel] = relationship("RunModel", back_populates="agents")
    actions: Mapped[list[ActionModel]] = relationship("ActionModel", back_populates="agent")
    findings: Mapped[list[FindingModel]] = relationship("FindingModel", back_populates="agent")


class ActionModel(Base):
    __tablename__ = "actions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    agent_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("agents.id"))
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    observation_summary: Mapped[str] = mapped_column(Text, nullable=False)
    thought: Mapped[str] = mapped_column(Text, nullable=False)
    tool: Mapped[str] = mapped_column(Enum(ActionTool), nullable=False)
    args: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    agent: Mapped[AgentModel] = relationship("AgentModel", back_populates="actions")


class FindingModel(Base):
    __tablename__ = "findings"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    run_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("runs.id"))
    agent_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    severity: Mapped[str] = mapped_column(Enum(Severity), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    repro_steps: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence_paths: Mapped[list[str]] = mapped_column(JSON, default=list)
    oracle_type: Mapped[str] = mapped_column(String(64), nullable=False)
    ground_truth_bug_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    llm_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    run: Mapped[RunModel] = relationship("RunModel", back_populates="findings")
    agent: Mapped[AgentModel | None] = relationship("AgentModel", back_populates="findings")


class BugCatalogModel(Base):
    __tablename__ = "bugs_catalog"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    sut: Mapped[str] = mapped_column(Enum(SUT), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    severity: Mapped[str] = mapped_column(Enum(Severity), nullable=False)
    location: Mapped[str] = mapped_column(String(512), nullable=False)
    repro: Mapped[str] = mapped_column(Text, nullable=False)
    detection_oracle: Mapped[str] = mapped_column(String(128), nullable=False)
    seeded_in_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
