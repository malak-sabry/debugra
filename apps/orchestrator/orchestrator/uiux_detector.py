from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from debugra_schemas import Finding, Severity
from orchestrator.config import get_settings

settings = get_settings()

# Only proceed if we have a model that definitely supports vision
_VISION_MODELS = {"claude", "gpt-4", "gpt-4o", "gpt-4v", "gemini-pro-vision"}

UIUX_PROMPT = """You are a UI/UX expert analyzing a screenshot of a web application.
Identify any UI/UX issues present in this screenshot. Focus on:

- Layout issues (misalignment, overlapping, broken grids)
- Visual inconsistencies (different fonts, colors, spacing)
- Truncated or overflowing text
- Poor contrast or readability problems
- Missing elements or empty states that should have content
- Styling that looks broken or incomplete
- Form issues (misaligned labels, missing validation indicators)
- Navigation issues (broken menus, unclear links)
- Responsive design problems visible in the viewport

For each issue found, return a JSON object with:
{
  "issues": [
    {
      "title": "Short descriptive title",
      "severity": "critical" | "high" | "medium" | "low" | "info",
      "description": "Detailed description of the issue",
      "location": "Where in the UI the issue appears"
    }
  ]
}

If no issues are found, return { "issues": [] }
Return ONLY valid JSON, no markdown or other text."""

_MAX_SCREENSHOTS = 10
_TIMEOUT_SECONDS = 120


async def analyze_screenshots_uiux(
    run_id: str,
    agent_results: list[dict[str, Any]],
) -> list[Finding]:
    """Analyze agent screenshots for UI/UX issues using an LLM with vision."""
    findings: list[Finding] = []

    if not settings.uiux_detection_enabled:
        return findings

    if not _has_vision_capable_llm():
        return findings

    seen_paths: set[str] = set()
    seen_titles: set[str] = set()
    analyzed = 0

    for agent_result in agent_results:
        if analyzed >= _MAX_SCREENSHOTS:
            break

        actions: list[dict] = agent_result.get("actions", [])
        role = agent_result.get("role", "unknown")
        agent_id = agent_result.get("agent_id")

        screenshot_paths = _collect_screenshots(actions, seen_paths)
        for path in screenshot_paths:
            if analyzed >= _MAX_SCREENSHOTS:
                break
            seen_paths.add(path)
            analyzed += 1

            issues = await _analyze_screenshot_with_timeout(path, role)
            if not issues:
                continue

            for issue in issues:
                title = issue.get("title", "UI/UX issue")
                if title in seen_titles:
                    continue
                seen_titles.add(title)

                findings.append(Finding(
                    id=uuid4(),
                    run_id=run_id,
                    agent_id=agent_id,
                    severity=_parse_severity(issue.get("severity", "low")),
                    title=f"[UI/UX] {title}",
                    description=issue.get("description", ""),
                    repro_steps=[],
                    evidence_paths=[path],
                    oracle_type="ui_ux_issue",
                    ground_truth_bug_id=None,
                    detected_at=datetime.now(timezone.utc),
                ))

    return findings


async def _analyze_screenshot_with_timeout(path: str, role: str) -> list[dict[str, str]]:
    try:
        return await asyncio.wait_for(
            _analyze_screenshot(path, role),
            timeout=_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return []
    except Exception:
        return []


def _has_vision_capable_llm() -> bool:
    # Claude models all support vision
    model = settings.llm_reporter.lower()
    if "claude" in model:
        key = settings.anthropic_api_key.strip()
        if key.startswith("sk-ant-") and "..." not in key:
            return True

    # OpenAI models that support vision
    if any(v in model for v in ("gpt-4", "gpt-4o", "gpt-4v")):
        okey = settings.openai_api_key.strip()
        if okey.startswith("sk-") and "..." not in okey:
            return True

    # HackClub proxy with explicit vision model
    hkey = settings.hackclub_api_key.strip()
    if hkey and "..." not in hkey:
        return True

    return False


def _pick_vision_provider() -> str:
    """Return the provider to use for vision: 'claude', 'openai', or 'hackclub'."""
    model = settings.llm_reporter.lower()
    if "claude" in model:
        key = settings.anthropic_api_key.strip()
        if key.startswith("sk-ant-") and "..." not in key:
            return "claude"

    if any(v in model for v in ("gpt-4", "gpt-4o", "gpt-4v")):
        okey = settings.openai_api_key.strip()
        if okey.startswith("sk-") and "..." not in okey:
            return "openai"

    hkey = settings.hackclub_api_key.strip()
    if hkey and "..." not in hkey:
        return "hackclub"

    return ""


def _pick_vision_model() -> str:
    provider = _pick_vision_provider()
    if provider == "hackclub":
        return settings.uiux_vision_model
    return settings.llm_reporter


def _collect_screenshots(actions: list[dict], seen: set[str]) -> list[str]:
    paths: list[str] = []
    for action in actions:
        sp = action.get("screenshot_path")
        if sp and sp not in seen:
            paths.append(sp)
    return paths


def _parse_severity(value: str) -> Severity:
    mapping = {
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
        "info": Severity.INFO,
    }
    return mapping.get(value.lower(), Severity.LOW)


async def _analyze_screenshot(path: str, role: str) -> list[dict[str, str]]:
    """Send a single screenshot to an LLM with vision and return found issues."""
    artifact_dir = Path(settings.artifacts_dir).resolve()
    full_path = (artifact_dir / path).resolve()

    if not full_path.exists() or not full_path.is_file():
        return []

    try:
        image_data = _encode_image(full_path)
    except Exception:
        return []

    provider = _pick_vision_provider()
    model = _pick_vision_model()

    if provider == "claude":
        return await _analyze_with_claude(image_data, model)
    elif provider == "openai":
        return await _analyze_with_openai(image_data, model, settings.openai_api_key, settings.openai_base_url)
    elif provider == "hackclub":
        return await _analyze_with_openai(image_data, model, settings.hackclub_api_key, settings.hackclub_base_url)
    return []


def _encode_image(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


async def _analyze_with_claude(image_data: str, model: str) -> list[dict[str, str]]:
    try:
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage

        llm = ChatAnthropic(
            model=model,
            api_key=settings.anthropic_api_key,
            max_tokens=1024,
            temperature=0,
            timeout=_TIMEOUT_SECONDS,
        )

        response = await llm.ainvoke([
            HumanMessage(
                content=[
                    {"type": "text", "text": UIUX_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_data}"},
                    },
                ]
            )
        ])
        return _parse_response(response.content)
    except Exception:
        return []


async def _analyze_with_openai(image_data: str, model: str, api_key: str, base_url: str) -> list[dict[str, str]]:
    try:
        from langchain_core.messages import HumanMessage
        from langchain_openai import ChatOpenAI

        if not api_key.strip():
            return []

        llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            max_tokens=1024,
            temperature=0,
            request_timeout=_TIMEOUT_SECONDS,
        )

        response = await llm.ainvoke([
            HumanMessage(
                content=[
                    {"type": "text", "text": UIUX_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_data}"},
                    },
                ]
            )
        ])
        return _parse_response(response.content)
    except Exception:
        return []


def _parse_response(content: str | list | dict) -> list[dict[str, str]]:
    import json

    raw = content
    if isinstance(raw, list):
        for block in raw:
            if isinstance(block, dict) and block.get("type") == "text":
                raw = block["text"]
                break
        else:
            return []

    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            result = json.loads(text)
            return result.get("issues", [])
        except json.JSONDecodeError:
            return []

    return []
