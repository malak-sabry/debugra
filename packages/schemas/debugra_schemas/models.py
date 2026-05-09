from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ─── Enumerations ────────────────────────────────────────────────────────────


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    DETECTING = "detecting"
    REPORTING = "reporting"
    COMPLETE = "complete"
    FAILED = "failed"


class AgentRole(str, enum.Enum):
    TEACHER = "teacher"
    STUDENT = "student"
    ADMIN = "admin"
    BUYER = "buyer"
    SELLER = "seller"
    ANONYMOUS = "anonymous"


class AgentStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    ABORTED = "aborted"


class ActionTool(str, enum.Enum):
    GOTO = "goto"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    WAIT_FOR = "wait_for"
    ASSERT_VISIBLE = "assert_visible"
    ASSERT_TEXT = "assert_text"
    UPLOAD = "upload"
    SCREENSHOT = "screenshot"
    SCROLL = "scroll"
    HOVER = "hover"
    PRESS = "press"


class Severity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SUT(str, enum.Enum):
    LMS = "lms"
    SHOP = "shop"


class RunEventType(str, enum.Enum):
    RUN_STARTED = "run_started"
    PLANNING_STARTED = "planning_started"
    PLANNING_COMPLETE = "planning_complete"
    AGENT_SPAWNED = "agent_spawned"
    AGENT_STEP = "agent_step"
    AGENT_SCREENSHOT = "agent_screenshot"
    AGENT_COMPLETE = "agent_complete"
    AGENT_FAILED = "agent_failed"
    FINDING_DETECTED = "finding_detected"
    REPORT_READY = "report_ready"
    RUN_COMPLETE = "run_complete"
    RUN_FAILED = "run_failed"
    LOG_LINE = "log_line"


# ─── Core Models ─────────────────────────────────────────────────────────────


class AgentObjective(BaseModel):
    role: AgentRole
    description: str
    steps: list[str]
    dependencies: list[str] = Field(default_factory=list)


class PlannerOutput(BaseModel):
    sut: SUT
    roles: list[AgentRole]
    objectives: list[AgentObjective]
    success_criteria: list[str]
    estimated_steps: int = 0


class Run(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    sut: SUT
    status: RunStatus = RunStatus.PENDING
    config: dict[str, Any] = Field(default_factory=dict)
    plan: PlannerOutput | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    artifact_dir: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Agent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    role: AgentRole
    status: AgentStatus = AgentStatus.PENDING
    model: str = "ollama/llama3.1:8b"
    step_count: int = 0
    trace_path: str | None = None
    video_path: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None


class Action(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    agent_id: UUID
    step: int
    observation_summary: str
    thought: str
    tool: ActionTool
    args: dict[str, Any]
    result: str | None = None
    error: str | None = None
    screenshot_path: str | None = None
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Finding(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    agent_id: UUID | None = None
    severity: Severity
    title: str
    description: str
    repro_steps: list[str]
    evidence_paths: list[str] = Field(default_factory=list)
    oracle_type: str  # "http_5xx" | "console_error" | "dom_assertion" | "axe" | "llm_unverified"
    ground_truth_bug_id: str | None = None
    llm_summary: str | None = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BugCatalogEntry(BaseModel):
    id: str  # e.g. "LMS-01"
    sut: SUT
    title: str
    severity: Severity
    location: str
    repro: str
    detection_oracle: str
    seeded_in_commit: str | None = None


# ─── WebSocket Event Envelope ─────────────────────────────────────────────────


class RunEvent(BaseModel):
    run_id: UUID
    type: RunEventType
    payload: dict[str, Any] = Field(default_factory=dict)
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
