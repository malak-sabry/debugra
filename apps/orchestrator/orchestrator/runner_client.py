from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Awaitable
from uuid import uuid4

from debugra_schemas import RunEventType
from orchestrator.config import get_settings

settings = get_settings()

# Path to agent-runner main
_AGENT_RUNNER_DIR = Path(__file__).parents[2] / "agent-runner"


async def run_agent(
    run_id: str,
    sut: str,
    base_url: str,
    objective: dict[str, Any],
    event_callback: Callable[[RunEventType, dict], Awaitable[None]] | None = None,
) -> dict[str, Any]:
    """
    Spawn an agent-runner subprocess and collect its output.
    
    The agent runner communicates via stdout as newline-delimited JSON events.
    """
    agent_id = str(uuid4())
    artifact_dir = Path(settings.artifacts_dir) / run_id / agent_id
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

                if etype == "agent_step":
                    actions.append(event.get("payload", {}))
                    if event_callback:
                        await event_callback(RunEventType.AGENT_STEP, event.get("payload", {}))

                elif etype == "agent_screenshot":
                    if event_callback:
                        await event_callback(RunEventType.AGENT_SCREENSHOT, event.get("payload", {}))

                elif etype == "log_line":
                    logs.append(event.get("payload", {}).get("line", ""))
                    if event_callback:
                        await event_callback(RunEventType.LOG_LINE, event.get("payload", {}))

                elif etype == "assertion_failure":
                    assertion_failures.append(event.get("payload", {}))

                elif etype == "axe_violation":
                    axe_violations.append(event.get("payload", {}))

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

    return {
        "agent_id": agent_id,
        "role": objective.get("role"),
        "actions": actions,
        "logs": logs,
        "assertion_failures": assertion_failures,
        "axe_violations": axe_violations,
        "artifact_dir": str(artifact_dir),
        "exit_code": proc.returncode,
    }
