from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.async_api import Page, TimeoutError as PWTimeout

from debugra_schemas import ActionTool


class ActionError(Exception):
    pass


async def execute_action(
    page: Page,
    tool: ActionTool,
    args: dict[str, Any],
    artifact_dir: Path,
    step: int,
) -> tuple[str, str | None, str | None]:
    """
    Execute a single action and return (result_text, screenshot_path, error).
    """
    screenshot_path: str | None = None

    try:
        match tool:
            case ActionTool.GOTO:
                url = args["url"]
                await page.goto(url, timeout=15_000, wait_until="domcontentloaded")
                result = f"Navigated to {url}"

            case ActionTool.CLICK:
                selector = args["selector"]
                await page.click(selector, timeout=10_000)
                result = f"Clicked {selector}"

            case ActionTool.FILL:
                selector = args["selector"]
                value = str(args["value"])
                await page.fill(selector, value, timeout=10_000)
                result = f"Filled {selector} with '{value}'"

            case ActionTool.SELECT:
                selector = args["selector"]
                value = str(args["value"])
                await page.select_option(selector, value, timeout=10_000)
                result = f"Selected '{value}' in {selector}"

            case ActionTool.WAIT_FOR:
                selector = args["selector"]
                timeout = int(args.get("timeout_ms", 5000))
                await page.wait_for_selector(selector, timeout=timeout)
                result = f"Waited for {selector}"

            case ActionTool.ASSERT_VISIBLE:
                selector = args["selector"]
                description = args.get("description", selector)
                try:
                    await page.wait_for_selector(selector, state="visible", timeout=5_000)
                    result = f"PASS: {description} is visible"
                except PWTimeout:
                    raise ActionError(f"FAIL: {description} not visible on page")

            case ActionTool.ASSERT_TEXT:
                selector = args["selector"]
                expected = str(args["expected"])
                partial = bool(args.get("partial", True))
                actual = await page.inner_text(selector, timeout=5_000)
                if partial:
                    ok = expected.lower() in actual.lower()
                else:
                    ok = actual.strip() == expected.strip()
                if not ok:
                    raise ActionError(f"FAIL: expected '{expected}' in '{actual[:100]}'")
                result = f"PASS: text matches '{expected}'"

            case ActionTool.UPLOAD:
                selector = args["selector"]
                file_path = args["file_path"]
                await page.set_input_files(selector, file_path, timeout=10_000)
                result = f"Uploaded {file_path}"

            case ActionTool.SCREENSHOT:
                label = args.get("label", f"step_{step}")
                safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
                path = artifact_dir / f"step_{step:03d}_{safe_label}.png"
                await page.screenshot(path=str(path), full_page=False)
                screenshot_path = str(path)
                result = f"Screenshot saved: {path.name}"

            case ActionTool.SCROLL:
                direction = args.get("direction", "down")
                amount = int(args.get("amount", 500))
                delta_y = amount if direction == "down" else -amount
                await page.evaluate(f"window.scrollBy(0, {delta_y})")
                result = f"Scrolled {direction} by {amount}px"

            case ActionTool.HOVER:
                selector = args["selector"]
                await page.hover(selector, timeout=10_000)
                result = f"Hovered over {selector}"

            case ActionTool.PRESS:
                key = args["key"]
                await page.keyboard.press(key)
                result = f"Pressed {key}"

            case _:
                raise ActionError(f"Unknown tool: {tool}")

        # Auto-screenshot after every non-screenshot action
        if tool != ActionTool.SCREENSHOT:
            auto_path = artifact_dir / f"step_{step:03d}_auto.png"
            try:
                await page.screenshot(path=str(auto_path), full_page=False)
                screenshot_path = str(auto_path)
            except Exception:
                pass

        return result, screenshot_path, None

    except ActionError as e:
        return "", screenshot_path, str(e)
    except PWTimeout as e:
        return "", screenshot_path, f"Timeout: {e}"
    except Exception as e:
        return "", screenshot_path, f"Error: {type(e).__name__}: {e}"
