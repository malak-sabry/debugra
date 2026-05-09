from __future__ import annotations

import json
from pathlib import Path

from debugra_schemas import PlannerOutput
from orchestrator.config import get_settings

settings = get_settings()

_PROMPT_PATH = Path(__file__).parents[3] / "packages" / "prompts" / "planner.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


async def run_planner(sut: str, readme: str, base_url: str) -> PlannerOutput:
    """Call the LLM planner and parse its JSON output into a PlannerOutput."""
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    system_prompt = _load_prompt()
    user_message = f"""SUT: {sut}
Base URL: {base_url}

README / Documentation:
---
{readme}
---

Produce the test plan JSON now."""

    llm = ChatAnthropic(
        model=settings.llm_planner,
        api_key=settings.anthropic_api_key,
        max_tokens=2048,
        temperature=0,
    )

    response = await llm.ainvoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
    )

    raw = response.content.strip()
    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    data = json.loads(raw)
    return PlannerOutput(**data)
