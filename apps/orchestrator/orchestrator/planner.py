from __future__ import annotations

import json
from pathlib import Path

from debugra_schemas import PlannerOutput
from orchestrator.config import get_settings

settings = get_settings()

_PROMPT_PATH = Path(__file__).parents[3] / "packages" / "prompts" / "planner.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _has_usable_anthropic_key() -> bool:
    key = settings.anthropic_api_key.strip()
    return key.startswith("sk-ant-") and "..." not in key


def _openai_compatible_config() -> tuple[str, str]:
    if settings.hackclub_api_key.strip():
        return settings.hackclub_api_key, settings.hackclub_base_url
    return settings.openai_api_key, settings.openai_base_url


async def run_planner(sut: str, readme: str, base_url: str) -> PlannerOutput:
    """Call the LLM planner and parse its JSON output into a PlannerOutput."""
    from langchain_core.messages import HumanMessage, SystemMessage

    system_prompt = _load_prompt()
    user_message = f"""SUT: {sut}
Base URL: {base_url}

README / Documentation:
---
{readme}
---

Produce the test plan JSON now."""

    model = settings.llm_planner
    if "claude" in model:
        if not _has_usable_anthropic_key():
            return _fallback_plan(sut)
        from langchain_anthropic import ChatAnthropic

        llm = ChatAnthropic(
            model=model,
            api_key=settings.anthropic_api_key,
            max_tokens=2048,
            temperature=0,
        )
    else:
        api_key, base_url = _openai_compatible_config()
        if not api_key.strip():
            return _fallback_plan(sut)
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            max_tokens=2048,
            temperature=0,
            request_timeout=60,
        )

    try:
        response = await llm.ainvoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
        )
    except Exception:
        return _fallback_plan(sut)

    raw = response.content.strip()
    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    data = json.loads(raw)
    return PlannerOutput(**data)


def _fallback_plan(sut: str) -> PlannerOutput:
    """Used for local/offline development when planner credentials are not configured."""
    if sut == "shop":
        return PlannerOutput(
            sut="shop",
            roles=["anonymous", "buyer"],
            objectives=[
                {
                    "role": "anonymous",
                    "description": "Browse the product catalog and inspect visible product information.",
                    "steps": [
                        "Open the shop home page",
                        "Review product cards",
                        "Verify login and register entry points are visible",
                    ],
                },
                {
                    "role": "buyer",
                    "description": "Exercise the buyer shopping flow from login through cart and checkout surfaces.",
                    "steps": [
                        "Open the shop home page",
                        "Attempt to add a product to cart",
                        "Inspect cart and checkout navigation",
                    ],
                    "dependencies": ["anonymous"],
                },
            ],
            success_criteria=[
                "Product catalog loads",
                "Buyer navigation is reachable",
                "No browser or API errors are observed",
            ],
            estimated_steps=12,
        )

    return PlannerOutput(
        sut="lms",
        roles=["teacher", "student", "admin"],
        objectives=[
            {
                "role": "teacher",
                "description": "Validate teacher registration, login, and course creation entry points.",
                "steps": [
                    "Open the LMS home page",
                    "Inspect sign-in and registration options",
                    "Navigate toward course management surfaces",
                ],
            },
            {
                "role": "student",
                "description": "Validate student access to assignments and submission surfaces.",
                "steps": [
                    "Open the LMS home page",
                    "Inspect student registration and login flow",
                    "Navigate toward assignments",
                ],
                "dependencies": ["teacher"],
            },
            {
                "role": "admin",
                "description": "Validate admin dashboard and user-management entry points.",
                "steps": [
                    "Open the LMS home page",
                    "Inspect admin login path",
                    "Navigate toward admin dashboard",
                ],
                "dependencies": ["teacher"],
            },
        ],
        success_criteria=[
            "Core role entry points are reachable",
            "Course and assignment surfaces are discoverable",
            "No browser or API errors are observed",
        ],
        estimated_steps=18,
    )
