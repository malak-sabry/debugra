from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestrator.config import get_settings

settings = get_settings()

_PROMPT_PATH = Path(__file__).parents[3] / "packages" / "prompts" / "reporter.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


async def run_reporter(
    run_id: str,
    sut: str,
    plan: dict[str, Any] | None,
    agent_results: list[dict[str, Any]],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Synthesize findings into a polished report via LLM."""
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    total_steps = sum(len(r.get("actions", [])) for r in agent_results)
    roles_tested = list({r.get("role", "unknown") for r in agent_results})

    user_message = f"""Run ID: {run_id}
SUT: {sut}
Total agents: {len(agent_results)}
Roles tested: {', '.join(roles_tested)}
Total actions: {total_steps}

Findings ({len(findings)} total):
{json.dumps(findings, indent=2, default=str)}

Produce the report JSON now."""

    if not settings.anthropic_api_key:
        return _fallback_report(run_id, sut, findings, roles_tested, total_steps)

    system_prompt = _load_prompt()
    llm = ChatAnthropic(
        model=settings.llm_reporter,
        api_key=settings.anthropic_api_key,
        max_tokens=4096,
        temperature=0,
    )

    response = await llm.ainvoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
    )

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)


def _fallback_report(
    run_id: str,
    sut: str,
    findings: list[dict],
    roles_tested: list[str],
    total_steps: int,
) -> dict[str, Any]:
    """Used when no API key is configured (dev/offline mode)."""
    severity_counts: dict[str, int] = {}
    for f in findings:
        s = f.get("severity", "info")
        severity_counts[s] = severity_counts.get(s, 0) + 1

    return {
        "findings": [
            {
                "id": f.get("id"),
                "severity": f.get("severity"),
                "title": f.get("title"),
                "summary": f.get("description"),
                "impact": "Requires investigation.",
                "repro_steps": f.get("repro_steps", []),
                "recommendation": "Investigate and fix the underlying issue.",
            }
            for f in findings
        ],
        "executive_summary": {
            "headline": f"Debugra found {len(findings)} issue(s) in {sut.upper()} across {len(roles_tested)} roles.",
            "total_findings": len(findings),
            "by_severity": severity_counts,
            "coverage_summary": f"Tested roles: {', '.join(roles_tested)}. Total steps: {total_steps}.",
            "top_risks": [f.get("title") for f in findings[:3]],
            "benchmark_note": "Run report (offline mode — LLM summarization disabled).",
        },
    }
