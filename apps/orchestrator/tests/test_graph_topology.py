"""Tests for the LangGraph topology and topological sort — no LLM/DB required."""
from __future__ import annotations

from orchestrator.graph import _topological_sort, build_run_graph
from debugra_schemas import AgentObjective, AgentRole


def _obj(role: str, deps: list[str]) -> AgentObjective:
    return AgentObjective(
        role=AgentRole(role),
        description=f"{role} objective",
        steps=[],
        dependencies=deps,
    )


def test_topological_sort_no_deps():
    objs = [_obj("teacher", []), _obj("student", []), _obj("admin", [])]
    result = _topological_sort(objs)
    assert len(result) == 3
    roles = [o.role for o in result]
    assert set(roles) == {AgentRole.TEACHER, AgentRole.STUDENT, AgentRole.ADMIN}


def test_topological_sort_with_dependency():
    objs = [
        _obj("student", ["teacher"]),
        _obj("teacher", []),
    ]
    result = _topological_sort(objs)
    roles = [o.role for o in result]
    teacher_idx = roles.index(AgentRole.TEACHER)
    student_idx = roles.index(AgentRole.STUDENT)
    assert teacher_idx < student_idx, "teacher must come before student"


def test_topological_sort_chain():
    objs = [
        _obj("admin", ["teacher"]),
        _obj("student", ["teacher"]),
        _obj("teacher", []),
    ]
    result = _topological_sort(objs)
    roles = [o.role for o in result]
    teacher_idx = roles.index(AgentRole.TEACHER)
    for role in [AgentRole.ADMIN, AgentRole.STUDENT]:
        assert teacher_idx < roles.index(role)


def test_topological_sort_handles_cycle_gracefully():
    """Cycles should not raise; remaining nodes appended at end."""
    objs = [
        _obj("teacher", ["student"]),
        _obj("student", ["teacher"]),
    ]
    result = _topological_sort(objs)
    assert len(result) == 2  # both nodes present, no crash


def test_build_run_graph_compiles():
    """Verify the LangGraph graph compiles without error."""
    graph = build_run_graph()
    assert graph is not None
