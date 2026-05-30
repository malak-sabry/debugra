from __future__ import annotations

from typing import Any
from uuid import uuid4

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from debugra_schemas import (
    Finding,
    PlannerOutput,
    RunEventType,
    Severity,
)
from orchestrator.planner import run_planner
from orchestrator.detector import aggregate_findings
from orchestrator.reporter import run_reporter
from orchestrator.uiux_detector import analyze_screenshots_uiux
from orchestrator.config import get_settings

settings = get_settings()


# ─── Graph State ──────────────────────────────────────────────────────────────


class RunState(TypedDict):
    run_id: str
    sut: str
    base_url: str
    readme_content: str
    plan: dict[str, Any] | None
    agent_results: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    report: dict[str, Any] | None
    error: str | None
    event_callback: Any  # async callable(RunEvent)


# ─── Node: plan ───────────────────────────────────────────────────────────────


async def node_plan(state: RunState) -> RunState:
    cb = state["event_callback"]
    if cb:
        await cb(RunEventType.PLANNING_STARTED, {})

    try:
        plan = await run_planner(
            sut=state["sut"],
            readme=state["readme_content"],
            base_url=state["base_url"],
        )
        state["plan"] = plan.model_dump()
        if cb:
            await cb(RunEventType.PLANNING_COMPLETE, {"plan": state["plan"]})
    except Exception as exc:
        state["error"] = f"Planning failed: {exc}"

    return state


# ─── Node: spawn_agents ───────────────────────────────────────────────────────


async def node_spawn_agents(state: RunState) -> RunState:
    """Spawn browser agent workers for each objective in the plan."""
    if state.get("error") or not state.get("plan"):
        return state

    plan = PlannerOutput(**state["plan"])
    cb = state["event_callback"]

    # Import here to avoid circular imports
    from orchestrator.runner_client import run_agent

    # Sort objectives by dependency order
    ordered = _topological_sort(plan.objectives)

    results: list[dict[str, Any]] = []

    # For now: run agents sequentially in dependency order.
    # Phase 2 will parallelize independent agents via asyncio.gather.
    for objective in ordered:
        agent_id = str(uuid4())
        role = objective.role.value if hasattr(objective.role, "value") else objective.role
        if cb:
            await cb(
                RunEventType.AGENT_SPAWNED,
                {
                    "agent_id": agent_id,
                    "role": role,
                    "description": objective.description,
                    "model": settings.llm_actor,
                    "status": "running",
                    "step_count": 0,
                },
            )

        try:
            result = await run_agent(
                run_id=state["run_id"],
                sut=state["sut"],
                base_url=state["base_url"],
                objective=objective.model_dump(),
                agent_id=agent_id,
                event_callback=cb,
            )
            results.append(result)
            if cb:
                exit_code = result.get("exit_code", 0)
                completion_type = (
                    RunEventType.AGENT_COMPLETE
                    if exit_code == 0
                    else RunEventType.AGENT_FAILED
                )
                await cb(
                    completion_type,
                    {
                        "agent_id": agent_id,
                        "role": role,
                        "step_count": len(result.get("actions", [])),
                        "trace_path": result.get("trace_path"),
                        "video_path": result.get("video_path"),
                        "exit_code": exit_code,
                    },
                )
                if exit_code != 0:
                    agent_actions = result.get("actions", [])
                    _build_agent_failure_finding(
                        cb=cb,
                        run_id=state["run_id"],
                        agent_id=agent_id,
                        role=role,
                        exit_code=exit_code,
                        actions=agent_actions,
                        error=result.get("error"),
                    )
        except Exception as exc:
            results.append({"agent_id": agent_id, "role": objective.role, "error": str(exc), "actions": [], "logs": []})
            if cb:
                await cb(
                    RunEventType.AGENT_FAILED,
                    {
                        "agent_id": agent_id,
                        "role": role,
                        "error": str(exc),
                    },
                )
                _build_agent_failure_finding(
                    cb=cb,
                    run_id=state["run_id"],
                    agent_id=agent_id,
                    role=role,
                    exit_code=-1,
                    actions=[],
                    error=str(exc),
                )

    state["agent_results"] = results
    return state


# ─── Node: detect ──────────────────────────────────────────────────────────────


async def node_detect(state: RunState) -> RunState:
    if state.get("error"):
        return state

    findings = await aggregate_findings(
        run_id=state["run_id"],
        agent_results=state["agent_results"],
    )

    uiux_findings = await analyze_screenshots_uiux(
        run_id=state["run_id"],
        agent_results=state["agent_results"],
    )
    findings.extend(uiux_findings)

    state["findings"] = [f.model_dump(mode="json") for f in findings]

    cb = state["event_callback"]
    if cb:
        for f in state["findings"]:
            await cb(RunEventType.FINDING_DETECTED, f)

    return state


# ─── Node: report ──────────────────────────────────────────────────────────────


async def node_report(state: RunState) -> RunState:
    if state.get("error"):
        return state

    report = await run_reporter(
        run_id=state["run_id"],
        sut=state["sut"],
        plan=state.get("plan"),
        agent_results=state["agent_results"],
        findings=state["findings"],
    )
    state["report"] = report

    cb = state["event_callback"]
    if cb:
        await cb(RunEventType.REPORT_READY, {"report": report})

    return state


# ─── Routing ───────────────────────────────────────────────────────────────────


def should_continue_after_plan(state: RunState) -> str:
    if state.get("error"):
        return "end"
    return "spawn_agents"


def should_continue_after_agents(state: RunState) -> str:
    if state.get("error"):
        return "end"
    return "detect"


# ─── Build Graph ───────────────────────────────────────────────────────────────


def build_run_graph() -> StateGraph:
    g = StateGraph(RunState)

    g.add_node("plan", node_plan)
    g.add_node("spawn_agents", node_spawn_agents)
    g.add_node("detect", node_detect)
    g.add_node("report", node_report)

    g.set_entry_point("plan")
    g.add_conditional_edges("plan", should_continue_after_plan, {"spawn_agents": "spawn_agents", "end": END})
    g.add_conditional_edges("spawn_agents", should_continue_after_agents, {"detect": "detect", "end": END})
    g.add_edge("detect", "report")
    g.add_edge("report", END)

    return g.compile()


# ─── Helpers ───────────────────────────────────────────────────────────────────


async def _build_agent_failure_finding(
    cb: Any,
    run_id: str,
    agent_id: str,
    role: str,
    exit_code: int,
    actions: list[dict],
    error: str | None,
) -> None:
    """Emit a FINDING_DETECTED with rich context about why the agent failed."""
    last_actions = actions[-5:] if actions else []

    # Translate exit codes
    if exit_code == -9:
        human_error = (
            "Agent hit the wall-clock time limit (5 min). "
            "It was still running when the timeout was reached."
        )
    elif exit_code == -1:
        human_error = f"Agent crashed before completing: {error or 'Unknown error'}"
    else:
        human_error = f"Agent exited with code {exit_code}. {error or ''}"

    # Build repro steps from last actions
    repro_steps: list[str] = []
    for a in last_actions:
        tool = a.get("tool", "?")
        step = a.get("step", "?")
        args = a.get("args", {})
        thought = a.get("thought", "")
        if tool == "goto":
            repro_steps.append(f"[{step}] Navigate to {args.get('url', '')}")
        elif tool == "click":
            repro_steps.append(f"[{step}] Click {args.get('selector', '')}")
        elif tool == "fill":
            repro_steps.append(f"[{step}] Fill {args.get('selector', '')} = '{args.get('value', '')[:80]}'")
        elif tool == "select":
            repro_steps.append(f"[{step}] Select {args.get('selector', '')} → '{args.get('value', '')}'")
        else:
            repro_steps.append(f"[{step}] {tool}: {str(args)[:100]}")
        if thought:
            repro_steps.append(f"     → reasoned: {thought[:150]}")

    # Collect unique evidence screenshots
    evidence_paths: list[str] = []
    for a in reversed(actions):
        sp = a.get("screenshot_path")
        if sp and sp not in evidence_paths:
            evidence_paths.append(sp)
            if len(evidence_paths) >= 3:
                break

    # Description with summary of what the agent was doing
    if last_actions:
        last_step = last_actions[-1]
        last_tool = last_step.get("tool", "?")
        last_args = last_step.get("args", {})
        last_obs = last_step.get("observation_summary", "?")
        context = (
            f"Agent role: {role}\n"
            f"Failure: {human_error}\n"
            f"Last action: {last_tool} on page {last_obs}\n"
            f"Last args: {str(last_args)[:200]}\n"
            f"Total steps attempted: {len(actions)}"
        )
    else:
        context = (
            f"Agent role: {role}\n"
            f"Failure: {human_error}\n"
            f"No actions were recorded before failure."
        )

    await cb(
        RunEventType.FINDING_DETECTED,
        Finding(
            id=uuid4(),
            run_id=run_id,
            agent_id=agent_id,
            severity=Severity.HIGH,
            title=f"Agent {role} failed: could not complete objective",
            description=context,
            repro_steps=repro_steps,
            evidence_paths=evidence_paths,
            oracle_type="agent_failure",
        ).model_dump(mode="json"),
    )


def _topological_sort(objectives: list) -> list:
    """Simple Kahn's algorithm for dependency ordering."""
    in_degree = {obj.role: len(obj.dependencies) for obj in objectives}
    queue = [obj for obj in objectives if in_degree[obj.role] == 0]
    result = []

    while queue:
        node = queue.pop(0)
        result.append(node)
        for obj in objectives:
            if node.role in obj.dependencies:
                in_degree[obj.role] -= 1
                if in_degree[obj.role] == 0:
                    queue.append(obj)

    # If there are remaining nodes (cycle), just append them
    remaining = [obj for obj in objectives if obj not in result]
    return result + remaining
