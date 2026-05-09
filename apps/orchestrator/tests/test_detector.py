"""Tests for the deterministic bug detector — no DB/network required."""
from __future__ import annotations

import pytest
import asyncio
from uuid import uuid4
from orchestrator.detector import aggregate_findings, _oracle_type
from debugra_schemas import Severity


# ─── oracle_type unit tests ────────────────────────────────────────────────────

def test_oracle_http_5xx():
    assert _oracle_type("[NET] GET /api/products → 500") == "http_5xx"
    assert _oracle_type("Response status 503 from server") == "http_5xx"


def test_oracle_js_exception():
    assert _oracle_type("TypeError: Cannot read property 'id' of undefined") == "js_exception"
    assert _oracle_type("ReferenceError: foo is not defined") == "js_exception"


def test_oracle_network_fail():
    assert _oracle_type("net::ERR_CONNECTION_REFUSED at http://localhost:8002") == "network_fail"
    assert _oracle_type("Failed to fetch /api/cart") == "network_fail"


def test_oracle_console_error():
    assert _oracle_type("[ERROR] Unhandled promise rejection") == "console_error"


def test_oracle_none_for_info():
    assert _oracle_type("[INFO] Page loaded successfully") is None
    assert _oracle_type("Navigating to /products") is None


# ─── aggregate_findings integration tests ─────────────────────────────────────

def run_async(coro):
    return asyncio.run(coro)


RUN_ID = str(uuid4())
AGENT_1 = str(uuid4())
AGENT_2 = str(uuid4())


def test_aggregate_empty():
    findings = run_async(aggregate_findings(RUN_ID, []))
    assert findings == []


def test_aggregate_http_5xx_from_log():
    agent_results = [
        {
            "agent_id": AGENT_1,
            "role": "buyer",
            "logs": ["[NET] POST /api/checkout → 500 Internal Server Error"],
            "actions": [],
            "assertion_failures": [],
        }
    ]
    findings = run_async(aggregate_findings(RUN_ID, agent_results))
    assert len(findings) == 1
    assert findings[0].oracle_type == "http_5xx"
    assert findings[0].severity == Severity.HIGH


def test_aggregate_deduplication():
    """Same log line appearing twice should produce only one finding."""
    line = "TypeError: Cannot read property 'price' of undefined"
    agent_results = [
        {
            "agent_id": AGENT_1,
            "role": "buyer",
            "logs": [line, line],
            "actions": [],
            "assertion_failures": [],
        }
    ]
    findings = run_async(aggregate_findings(RUN_ID, agent_results))
    assert len(findings) == 1


def test_aggregate_assertion_failures():
    agent_results = [
        {
            "agent_id": AGENT_2,
            "role": "student",
            "logs": [],
            "actions": [],
            "assertion_failures": [
                {
                    "description": "Course title should be visible",
                    "detail": "FAIL: element not found",
                    "repro_steps": ["Navigate to /", "Click course"],
                    "evidence_paths": ["/runs/r1/agent-2/step_005_auto.png"],
                }
            ],
        }
    ]
    findings = run_async(aggregate_findings(RUN_ID, agent_results))
    assert len(findings) == 1
    assert findings[0].oracle_type == "dom_assertion"
    assert findings[0].severity == Severity.MEDIUM


def test_aggregate_axe_violations():
    agent_results = [
        {
            "agent_id": AGENT_1,
            "role": "student",
            "logs": [],
            "actions": [],
            "assertion_failures": [],
            "axe_violations": [
                {
                    "description": "Images must have alternate text",
                    "detail": "Rule: image-alt · Impact: critical · 3 element(s) affected",
                    "repro_steps": ["Navigate to http://localhost:3001"],
                    "oracle_type": "axe_violation",
                    "impact": "critical",
                },
                {
                    "description": "Form elements must have labels",
                    "detail": "Rule: label · Impact: serious · 2 element(s) affected",
                    "repro_steps": ["Navigate to http://localhost:3001/login"],
                    "oracle_type": "axe_violation",
                    "impact": "serious",
                },
            ],
        }
    ]
    findings = run_async(aggregate_findings(RUN_ID, agent_results))
    assert len(findings) == 2
    oracles = {f.oracle_type for f in findings}
    assert oracles == {"axe_violation"}
    severities = {f.severity for f in findings}
    from debugra_schemas import Severity
    assert Severity.CRITICAL in severities
    assert Severity.HIGH in severities
    for f in findings:
        assert f.title.startswith("[a11y]")


def test_aggregate_axe_deduplication():
    """Same violation description from two agents → only one finding."""
    same_violation = {
        "description": "Images must have alternate text",
        "detail": "Rule: image-alt · Impact: critical · 1 element(s) affected",
        "repro_steps": ["Navigate to /"],
        "oracle_type": "axe_violation",
        "impact": "critical",
    }
    agent_results = [
        {"agent_id": AGENT_1, "role": "teacher", "logs": [], "actions": [], "assertion_failures": [], "axe_violations": [same_violation]},
        {"agent_id": AGENT_2, "role": "student", "logs": [], "actions": [], "assertion_failures": [], "axe_violations": [same_violation]},
    ]
    findings = run_async(aggregate_findings(RUN_ID, agent_results))
    assert len(findings) == 1


def test_aggregate_multiple_agents():
    agent_results = [
        {
            "agent_id": AGENT_1,
            "role": "teacher",
            "logs": ["HTTP 500 on POST /api/assignments"],
            "actions": [],
            "assertion_failures": [],
        },
        {
            "agent_id": AGENT_2,
            "role": "student",
            "logs": ["net::ERR_CONNECTION_REFUSED http://localhost:8001/api/courses"],
            "actions": [],
            "assertion_failures": [],
        },
    ]
    findings = run_async(aggregate_findings(RUN_ID, agent_results))
    oracle_types = {f.oracle_type for f in findings}
    assert "http_5xx" in oracle_types
    assert "network_fail" in oracle_types
