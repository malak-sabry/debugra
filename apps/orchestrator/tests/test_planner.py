"""Planner fallback behavior for local development."""

from debugra_schemas import SUT
from orchestrator.planner import _fallback_plan


def test_fallback_plan_for_lms():
    plan = _fallback_plan("lms")

    assert plan.sut == SUT.LMS
    assert len(plan.objectives) >= 3
    assert plan.estimated_steps > 0


def test_fallback_plan_for_shop():
    plan = _fallback_plan("shop")

    assert plan.sut == SUT.SHOP
    assert len(plan.objectives) >= 2
    assert plan.estimated_steps > 0
