from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Awaitable
from uuid import uuid4

from debugra_schemas import RunEventType
from orchestrator.config import get_settings

settings = get_settings()

# Path to agent-runner main
_AGENT_RUNNER_DIR = Path(__file__).parents[2] / "agent-runner"


def _artifact_ref(path: Path) -> str:
    try:
        return str(path.relative_to(Path(settings.artifacts_dir).resolve()))
    except ValueError:
        return str(path)


async def run_agent(
    run_id: str,
    sut: str,
    base_url: str,
    objective: dict[str, Any],
    agent_id: str | None = None,
    event_callback: Callable[[RunEventType, dict], Awaitable[None]] | None = None,
) -> dict[str, Any]:
    """
    Spawn an agent-runner subprocess and collect its output.
    
    The agent runner communicates via stdout as newline-delimited JSON events.
    """
    agent_id = agent_id or str(uuid4())
    role = objective.get("role")
    role_value = getattr(role, "value", role)
    artifact_dir = (Path(settings.artifacts_dir) / run_id / agent_id).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)

    env = {**os.environ, "PYTHONUNBUFFERED": "1"}

    cmd = [
        sys.executable,
        "-m",
        "runner.main",
        "--run-id", run_id,
        "--agent-id", agent_id,
        "--sut", sut,
        "--base-url", base_url,
        "--objective", json.dumps(objective),
        "--artifact-dir", str(artifact_dir),
        "--step-limit", str(settings.agent_step_limit),
        "--headless", str(settings.playwright_headless).lower(),
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd=str(_AGENT_RUNNER_DIR),
    )

    actions: list[dict] = []
    logs: list[str] = []
    assertion_failures: list[dict] = []
    axe_violations: list[dict] = []

    async def read_stdout():
        assert proc.stdout
        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                etype = event.get("type")
                payload = event.get("payload", {})

                if etype == "agent_step":
                    payload = {"agent_id": agent_id, "role": role_value, **payload}
                    actions.append(payload)
                    if event_callback:
                        await event_callback(RunEventType.AGENT_STEP, payload)

                elif etype == "agent_screenshot":
                    payload = {"agent_id": agent_id, "role": role_value, **payload}
                    if event_callback:
                        await event_callback(RunEventType.AGENT_SCREENSHOT, payload)

                elif etype == "log_line":
                    payload = {"agent_id": agent_id, "role": role_value, **payload}
                    logs.append(payload.get("line", ""))
                    if event_callback:
                        await event_callback(RunEventType.LOG_LINE, payload)

                elif etype == "assertion_failure":
                    assertion_failures.append(payload)

                elif etype == "axe_violation":
                    axe_violations.append(payload)

            except json.JSONDecodeError:
                logs.append(line)

    try:
        await asyncio.wait_for(
            read_stdout(),
            timeout=settings.agent_wall_clock_seconds,
        )
    except asyncio.TimeoutError:
        proc.kill()

    await proc.wait()
    trace_path = artifact_dir / "trace.zip"
    video_path = next(artifact_dir.glob("*.webm"), None)

    return {
        "agent_id": agent_id,
        "role": role_value,
        "actions": actions,
        "logs": logs,
        "assertion_failures": assertion_failures,
        "axe_violations": axe_violations,
        "artifact_dir": str(artifact_dir),
        "trace_path": _artifact_ref(trace_path) if trace_path.exists() else None,
        "video_path": _artifact_ref(video_path) if video_path else None,
        "exit_code": proc.returncode,
    }
