from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestrator.config import get_settings

settings = get_settings()

_PROMPT_PATH = Path(__file__).parents[3] / "packages" / "prompts" / "reporter.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _has_usable_anthropic_key() -> bool:
    key = settings.anthropic_api_key.strip()
    return key.startswith("sk-ant-") and "..." not in key


def _openai_compatible_config() -> tuple[str, str]:
    if settings.hackclub_api_key.strip():
        return settings.hackclub_api_key, settings.hackclub_base_url
    return settings.openai_api_key, settings.openai_base_url


async def run_reporter(
    run_id: str,
    sut: str,
    plan: dict[str, Any] | None,
    agent_results: list[dict[str, Any]],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Synthesize findings into a polished report via LLM."""
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

    system_prompt = _load_prompt()
    model = settings.llm_reporter
    if "claude" in model:
        if not _has_usable_anthropic_key():
            return _fallback_report(run_id, sut, findings, roles_tested, total_steps)
        from langchain_anthropic import ChatAnthropic

        llm = ChatAnthropic(
            model=model,
            api_key=settings.anthropic_api_key,
            max_tokens=4096,
            temperature=0,
        )
    else:
        api_key, base_url = _openai_compatible_config()
        if not api_key.strip():
            return _fallback_report(run_id, sut, findings, roles_tested, total_steps)
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            max_tokens=4096,
            temperature=0,
            request_timeout=60,
        )

    try:
        response = await llm.ainvoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
        )
    except Exception:
        return _fallback_report(run_id, sut, findings, roles_tested, total_steps)

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
