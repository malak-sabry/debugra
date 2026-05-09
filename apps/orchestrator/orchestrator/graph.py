from __future__ import annotations

import asyncio
from typing import Annotated, Any
from uuid import UUID

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from debugra_schemas import (
    AgentRole,
    AgentStatus,
    Finding,
    PlannerOutput,
    Run,
    RunEventType,
    RunStatus,
    SUT,
)
from orchestrator.planner import run_planner
from orchestrator.detector import aggregate_findings
from orchestrator.reporter import run_reporter


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
        if cb:
            await cb(RunEventType.AGENT_SPAWNED, {"role": objective.role, "description": objective.description})

        try:
            result = await run_agent(
                run_id=state["run_id"],
                sut=state["sut"],
                base_url=state["base_url"],
                objective=objective.model_dump(),
                event_callback=cb,
            )
            results.append(result)
        except Exception as exc:
            results.append({"role": objective.role, "error": str(exc), "actions": [], "logs": []})

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


def _topological_sort(objectives: list) -> list:
    """Simple Kahn's algorithm for dependency ordering."""
    role_to_obj = {obj.role: obj for obj in objectives}
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
