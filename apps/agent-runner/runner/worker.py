from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, Page

from debugra_schemas import ActionTool
from runner.observer import snapshot_page
from runner.actions import execute_action


def _emit(event_type: str, payload: dict[str, Any]) -> None:
    """Write a newline-delimited JSON event to stdout."""
    print(json.dumps({"type": event_type, "payload": payload, "ts": datetime.now(timezone.utc).isoformat()}), flush=True)


class BrowserAgent:
    def __init__(
        self,
        run_id: str,
        agent_id: str,
        sut: str,
        base_url: str,
        objective: dict[str, Any],
        artifact_dir: Path,
        step_limit: int = 40,
        headless: bool = True,
        actor_model: str = "ollama/llama3.1:8b",
    ):
        self.run_id = run_id
        self.agent_id = agent_id
        self.sut = sut
        self.base_url = base_url
        self.objective = objective
        self.artifact_dir = artifact_dir
        self.step_limit = step_limit
        self.headless = headless
        self.actor_model = actor_model

        self.role: str = objective.get("role", "anonymous")
        self.objective_description: str = objective.get("description", "")
        self.objective_steps: list[str] = objective.get("steps", [])

        self._console_logs: list[str] = []
        self._network_errors: list[str] = []
        self._assertion_failures: list[dict] = []
        self._axe_violations: list[dict] = []
        self._actions: list[dict] = []

    async def run(self) -> dict[str, Any]:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            har_path = self.artifact_dir / "network.har"
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                record_video_dir=str(self.artifact_dir),
                record_video_size={"width": 1280, "height": 800},
                record_har_path=str(har_path),
                record_har_url_filter="**/*",
            )

            # Playwright trace
            await context.tracing.start(screenshots=True, snapshots=True, sources=False)

            page = await context.new_page()
            self._attach_listeners(page)

            await self._execute_loop(page)

            # Save trace and HAR (context.close() flushes HAR)
            trace_path = self.artifact_dir / "trace.zip"
            await context.tracing.stop(path=str(trace_path))
            await context.close()  # also finalises network.har
            await browser.close()

        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "actions": self._actions,
            "logs": self._console_logs + self._network_errors,
            "assertion_failures": self._assertion_failures,
            "axe_violations": self._axe_violations,
            "trace_path": str(trace_path),
            "har_path": str(har_path),
        }

    def _attach_listeners(self, page: Page) -> None:
        def on_console(msg):
            line = f"[{msg.type.upper()}] {msg.text}"
            self._console_logs.append(line)
            _emit("log_line", {"role": self.role, "line": line, "source": "console"})

        def on_request_failed(req):
            line = f"[NET_FAIL] {req.method} {req.url}: {req.failure}"
            self._network_errors.append(line)
            _emit("log_line", {"role": self.role, "line": line, "source": "network"})

        page.on("console", on_console)
        page.on("requestfailed", on_request_failed)

    async def _run_axe(self, page: Page, step: int) -> None:
        """Run axe-core on the current page and collect accessibility violations."""
        try:
            from axe_playwright_python.sync_playwright import Axe
            axe = Axe()
            await page.evaluate(axe.source)
            results: dict = await page.evaluate("() => axe.run()")
            violations: list[dict] = results.get("violations", [])
            for v in violations:
                impact = v.get("impact", "minor")
                description = v.get("description", v.get("help", "a11y violation"))
                rule_id = v.get("id", "unknown")
                nodes_count = len(v.get("nodes", []))
                line = f"[AXE] {impact}: {description} (rule: {rule_id}, {nodes_count} element(s))"
                self._console_logs.append(line)
                _emit("log_line", {"role": self.role, "line": line, "source": "axe"})
                violation_record = {
                    "description": description,
                    "detail": f"Rule: {rule_id} · Impact: {impact} · {nodes_count} element(s) affected",
                    "repro_steps": [f"Navigate to {page.url}"],
                    "evidence_paths": [],
                    "oracle_type": "axe_violation",
                    "impact": impact,
                }
                self._axe_violations.append(violation_record)
                _emit("axe_violation", violation_record)
        except Exception as exc:
            _emit("log_line", {"role": self.role, "line": f"[AXE] scan skipped: {exc}", "source": "axe"})

    async def _execute_loop(self, page: Page) -> None:
        action_history: list[str] = []
        _emit("log_line", {"role": self.role, "line": f"Agent started: {self.role} — {self.objective_description}", "source": "agent"})

        # Navigate to base URL first
        try:
            await page.goto(self.base_url, timeout=15_000, wait_until="domcontentloaded")
        except Exception as e:
            _emit("log_line", {"role": self.role, "line": f"Failed to load base URL: {e}", "source": "agent"})
            return

        for step in range(1, self.step_limit + 1):
            obs = await snapshot_page(page)

            # Build compact action history string
            history_str = "\n".join(action_history[-5:]) if action_history else "None"

            # Call LLM for next action
            try:
                decision = await self._think(obs, history_str, step)
            except Exception as e:
                _emit("log_line", {"role": self.role, "line": f"LLM error at step {step}: {e}", "source": "agent"})
                break

            tool_str = decision.get("tool", "screenshot")
            thought = decision.get("thought", "")
            args = decision.get("args", {})

            try:
                tool = ActionTool(tool_str)
            except ValueError:
                tool = ActionTool.SCREENSHOT
                args = {"label": "unknown_tool"}

            result, screenshot_path, error = await execute_action(
                page, tool, args, self.artifact_dir, step
            )

            # Run axe after navigation actions
            if tool == ActionTool.GOTO and not error:
                await self._run_axe(page, step)

            action_record = {
                "step": step,
                "observation_summary": obs["url"],
                "thought": thought,
                "tool": tool_str,
                "args": args,
                "result": result,
                "error": error,
                "screenshot_path": screenshot_path,
            }
            self._actions.append(action_record)

            # Assertion failures
            if error and tool in (ActionTool.ASSERT_VISIBLE, ActionTool.ASSERT_TEXT):
                failure = {
                    "description": args.get("description", f"Assertion at step {step}"),
                    "detail": error,
                    "repro_steps": [h for h in action_history[-3:]],
                    "evidence_paths": [screenshot_path] if screenshot_path else [],
                }
                self._assertion_failures.append(failure)
                _emit("assertion_failure", failure)

            _emit("agent_step", action_record)

            if screenshot_path:
                _emit("agent_screenshot", {
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "step": step,
                    "path": screenshot_path,
                })

            summary = f"Step {step}: {tool_str}({json.dumps(args)[:60]}) → {(result or error or '')[:80]}"
            action_history.append(summary)

            # Stop if objective complete
            if args.get("label") == "objective_complete":
                _emit("log_line", {"role": self.role, "line": "Objective complete.", "source": "agent"})
                break

            if error and "FAIL:" in str(error):
                # Non-fatal assertion failure; continue
                pass

    async def _think(self, obs: dict[str, Any], history: str, step: int) -> dict[str, Any]:
        """Call the actor LLM and return the next action dict."""
        from pathlib import Path as _Path

        prompt_path = _Path(__file__).parents[3] / "packages" / "prompts" / "actor.md"
        template = prompt_path.read_text(encoding="utf-8")

        prompt = (
            template
            .replace("{{role}}", self.role)
            .replace("{{objective}}", self.objective_description)
            .replace("{{step}}", str(step))
            .replace("{{step_limit}}", str(self.step_limit))
            .replace("{{current_url}}", obs.get("url", ""))
            .replace("{{page_title}}", obs.get("title", ""))
            .replace("{{dom_snapshot}}", obs.get("dom_snapshot", "")[:6000])
            .replace("{{interactable_elements}}", json.dumps(obs.get("interactable_elements", []), indent=2)[:6000])
            .replace("{{action_history}}", history)
        )

        if self.actor_model.startswith("ollama/"):
            return await self._call_ollama(prompt)
        elif "claude" in self.actor_model:
            return await self._call_anthropic(prompt)
        else:
            return await self._call_openai(prompt)

    async def _call_ollama(self, prompt: str) -> dict[str, Any]:
        import httpx
        import os
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model = self.actor_model.replace("ollama/", "")
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False, "format": "json"},
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "{}")
            return json.loads(raw)

    async def _call_anthropic(self, prompt: str) -> dict[str, Any]:
        import os
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage
        llm = ChatAnthropic(model=self.actor_model, api_key=os.environ.get("ANTHROPIC_API_KEY", ""), max_tokens=512, temperature=0)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        return json.loads(raw)

    async def _call_openai(self, prompt: str) -> dict[str, Any]:
        import os
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage
        api_key = os.environ.get("HACKCLUB_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("HACKCLUB_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        llm = ChatOpenAI(
            model=self.actor_model,
            api_key=api_key,
            base_url=base_url,
            max_tokens=512,
            temperature=0,
            request_timeout=60,
        )
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        return json.loads(raw)
