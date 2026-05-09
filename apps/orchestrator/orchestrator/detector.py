from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import uuid4

from debugra_schemas import Finding, Severity


# ─── Deterministic Oracles ───────────────────────────────────────────────────

_HTTP_5XX_RE = re.compile(r"\b5\d{2}\b")
_CONSOLE_ERROR_RE = re.compile(r"(error|exception|unhandled|uncaught)", re.IGNORECASE)
_NETWORK_FAIL_RE = re.compile(r"(net::ERR|failed to fetch|NetworkError)", re.IGNORECASE)
_JS_EXCEPTION_RE = re.compile(r"(TypeError|ReferenceError|SyntaxError|RangeError):", re.IGNORECASE)


def _oracle_type(log_line: str) -> str | None:
    if _HTTP_5XX_RE.search(log_line):
        return "http_5xx"
    if _JS_EXCEPTION_RE.search(log_line):
        return "js_exception"
    if _NETWORK_FAIL_RE.search(log_line):
        return "network_fail"
    if _CONSOLE_ERROR_RE.search(log_line):
        return "console_error"
    return None


def _axe_severity(impact: str) -> Severity:
    """Map axe-core impact level → Severity."""
    return {
        "critical": Severity.CRITICAL,
        "serious": Severity.HIGH,
        "moderate": Severity.MEDIUM,
        "minor": Severity.LOW,
    }.get(impact, Severity.LOW)


def _severity_for_oracle(oracle: str) -> Severity:
    mapping = {
        "http_5xx": Severity.HIGH,
        "js_exception": Severity.HIGH,
        "network_fail": Severity.MEDIUM,
        "console_error": Severity.MEDIUM,
        "dom_assertion": Severity.MEDIUM,
        "axe_violation": Severity.LOW,
        "llm_unverified": Severity.INFO,
    }
    return mapping.get(oracle, Severity.INFO)


# ─── Aggregate Findings ──────────────────────────────────────────────────────


async def aggregate_findings(run_id: str, agent_results: list[dict]) -> list[Finding]:
    """Process all agent results and extract Finding objects."""
    findings: list[Finding] = []
    seen_titles: set[str] = set()

    for agent_result in agent_results:
        role = agent_result.get("role", "unknown")
        agent_id = agent_result.get("agent_id")
        logs: list[str] = agent_result.get("logs", [])
        actions: list[dict] = agent_result.get("actions", [])
        assertion_failures: list[dict] = agent_result.get("assertion_failures", [])

        # 1. Scan logs for deterministic oracle hits
        for log_line in logs:
            oracle = _oracle_type(log_line)
            if oracle:
                title = _make_title(oracle, log_line, role)
                if title in seen_titles:
                    continue
                seen_titles.add(title)

                findings.append(Finding(
                    id=uuid4(),
                    run_id=run_id,
                    agent_id=agent_id,
                    severity=_severity_for_oracle(oracle),
                    title=title,
                    description=f"Detected via {oracle}: {log_line[:200]}",
                    repro_steps=_extract_repro_steps(actions, log_line),
                    evidence_paths=_extract_screenshots(actions),
                    oracle_type=oracle,
                    ground_truth_bug_id=None,
                    detected_at=datetime.now(timezone.utc),
                ))

        # 2. Assertion failures from agent actions
        for failure in assertion_failures:
            title = failure.get("description", "Assertion failed")
            if title in seen_titles:
                continue
            seen_titles.add(title)

            findings.append(Finding(
                id=uuid4(),
                run_id=run_id,
                agent_id=agent_id,
                severity=Severity.MEDIUM,
                title=title,
                description=failure.get("detail", ""),
                repro_steps=failure.get("repro_steps", []),
                evidence_paths=failure.get("evidence_paths", []),
                oracle_type="dom_assertion",
                ground_truth_bug_id=failure.get("bug_id"),
                detected_at=datetime.now(timezone.utc),
            ))

        # 3. Axe-core accessibility violations
        axe_violations: list[dict] = agent_result.get("axe_violations", [])
        for violation in axe_violations:
            title = violation.get("description", "Accessibility violation")
            if title in seen_titles:
                continue
            seen_titles.add(title)

            impact = violation.get("impact", "minor")
            severity = _axe_severity(impact)

            findings.append(Finding(
                id=uuid4(),
                run_id=run_id,
                agent_id=agent_id,
                severity=severity,
                title=f"[a11y] {title}",
                description=violation.get("detail", title),
                repro_steps=violation.get("repro_steps", []),
                evidence_paths=[],
                oracle_type="axe_violation",
                ground_truth_bug_id=None,
                detected_at=datetime.now(timezone.utc),
            ))

    return findings


def _make_title(oracle: str, log_line: str, role: str) -> str:
    if oracle == "http_5xx":
        match = _HTTP_5XX_RE.search(log_line)
        code = match.group(0) if match else "5xx"
        return f"HTTP {code} error encountered by {role}"
    if oracle == "js_exception":
        match = _JS_EXCEPTION_RE.search(log_line)
        exc_type = match.group(1) if match else "Exception"
        return f"{exc_type} in browser (role: {role})"
    if oracle == "network_fail":
        return f"Network request failed (role: {role})"
    return f"Console error detected (role: {role})"


def _extract_repro_steps(actions: list[dict], log_line: str) -> list[str]:
    """Return the last 3 actions before this error as repro steps."""
    steps = []
    for action in actions[-3:]:
        tool = action.get("tool", "")
        args = action.get("args", {})
        if tool == "goto":
            steps.append(f"Navigate to {args.get('url', '')}")
        elif tool == "click":
            steps.append(f"Click {args.get('selector', '')}")
        elif tool == "fill":
            steps.append(f"Fill {args.get('selector', '')} with '{args.get('value', '')}'")
        else:
            steps.append(f"{tool}: {args}")
    return steps or ["Reproduce by following the agent's action sequence"]


def _extract_screenshots(actions: list[dict]) -> list[str]:
    return [a["screenshot_path"] for a in actions if a.get("screenshot_path")]
