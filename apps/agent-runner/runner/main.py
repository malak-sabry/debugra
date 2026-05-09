from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[3] / ".env")

from runner.worker import BrowserAgent


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Debugra agent runner")
    p.add_argument("--run-id", required=True)
    p.add_argument("--agent-id", required=True)
    p.add_argument("--sut", required=True)
    p.add_argument("--base-url", required=True)
    p.add_argument("--objective", required=True, help="JSON-encoded AgentObjective")
    p.add_argument("--artifact-dir", required=True)
    p.add_argument("--step-limit", type=int, default=40)
    p.add_argument("--headless", default="true")
    p.add_argument("--actor-model", default=os.environ.get("LLM_ACTOR", "ollama/llama3.1:8b"))
    return p.parse_args()


async def main() -> None:
    args = parse_args()
    objective = json.loads(args.objective)
    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    headless = args.headless.lower() not in ("false", "0", "no")

    agent = BrowserAgent(
        run_id=args.run_id,
        agent_id=args.agent_id,
        sut=args.sut,
        base_url=args.base_url,
        objective=objective,
        artifact_dir=artifact_dir,
        step_limit=args.step_limit,
        headless=headless,
        actor_model=args.actor_model,
    )

    result = await agent.run()
    # Final summary event
    print(json.dumps({"type": "agent_complete", "payload": {"agent_id": args.agent_id, "role": objective.get("role"), "step_count": len(result["actions"])}}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
