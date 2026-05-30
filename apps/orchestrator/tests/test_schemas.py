"""Smoke tests for debugra_schemas — no DB/network required."""
from __future__ import annotations

from debugra_schemas import (
    AgentObjective,
    AgentRole,
    ActionTool,
    Finding,
    PlannerOutput,
    Run,
    RunEventType,
    RunStatus,
    Severity,
    SUT,
)
from uuid import uuid4


def test_run_status_values():
    assert RunStatus.PENDING == "pending"
    assert RunStatus.COMPLETE == "complete"
    assert RunStatus.FAILED == "failed"


def test_run_model_defaults():
    run = Run(sut=SUT.LMS)
    assert run.status == RunStatus.PENDING
    assert run.plan is None
    assert isinstance(run.id, object)


def test_planner_output_round_trip():
    plan = PlannerOutput(
        sut=SUT.LMS,
        roles=[AgentRole.TEACHER, AgentRole.STUDENT],
        objectives=[
            AgentObjective(
                role=AgentRole.TEACHER,
                description="Create a course",
                steps=["Navigate to /courses/create", "Fill form", "Submit"],
                dependencies=[],
            ),
            AgentObjective(
                role=AgentRole.STUDENT,
                description="Enroll in course",
                steps=["Navigate to /", "Click enroll"],
                dependencies=["teacher"],
            ),
        ],
        success_criteria=["Course visible to student"],
        estimated_steps=10,
    )
    assert plan.sut == SUT.LMS
    assert len(plan.objectives) == 2
    assert plan.objectives[1].dependencies == ["teacher"]

    dumped = plan.model_dump()
    restored = PlannerOutput(**dumped)
    assert restored.estimated_steps == 10


def test_finding_construction():
    run_id = uuid4()
    f = Finding(
        run_id=run_id,
        severity=Severity.HIGH,
        title="HTTP 500 on checkout",
        description="POST /api/checkout returns 500",
        repro_steps=["Add item to cart", "Submit checkout"],
        oracle_type="http_5xx",
    )
    assert f.severity == Severity.HIGH
    assert f.ground_truth_bug_id is None


def test_run_event_type_completeness():
    expected = {
        "run_started", "planning_started", "planning_complete",
        "agent_spawned", "agent_step", "agent_screenshot",
        "agent_complete", "agent_failed", "finding_detected",
        "report_ready", "run_complete", "run_failed", "log_line",
    }
    actual = {e.value for e in RunEventType}
    assert expected == actual


def test_action_tool_values():
    tools = {e.value for e in ActionTool}
    assert "goto" in tools
    assert "click" in tools
    assert "assert_visible" in tools
    assert "assert_text" in tools
