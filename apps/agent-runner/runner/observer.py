from __future__ import annotations

from typing import Any

from playwright.async_api import Page


# Max token budget for DOM snapshot (approx chars / 4 ≈ tokens)
_MAX_SNAPSHOT_CHARS = 12_000


async def snapshot_page(page: Page) -> dict[str, Any]:
    """Return a compact representation of the current page state."""
    url = page.url
    title = await page.title()

    # Accessibility tree (most token-efficient)
    try:
        a11y = await page.accessibility.snapshot(interesting_only=True)
        dom_text = _flatten_a11y(a11y or {})
    except Exception:
        dom_text = ""

    # Fallback: inner text of body
    if not dom_text:
        try:
            dom_text = await page.inner_text("body")
        except Exception:
            dom_text = ""

    # Collect interactive elements
    try:
        interactables = await page.evaluate(_JS_INTERACTABLE_ELEMENTS)
    except Exception:
        interactables = []

    # Collect console errors accumulated on the page
    snapshot = {
        "url": url,
        "title": title,
        "dom_snapshot": _truncate(dom_text, _MAX_SNAPSHOT_CHARS),
        "interactable_elements": interactables[:50],  # cap
    }

    return snapshot


def _flatten_a11y(node: dict, depth: int = 0, max_depth: int = 8) -> str:
    if depth > max_depth:
        return ""
    indent = "  " * depth
    role = node.get("role", "")
    name = node.get("name", "")
    value = node.get("value", "")
    desc = node.get("description", "")

    parts = [role]
    if name:
        parts.append(f'"{name}"')
    if value:
        parts.append(f"= {value}")
    if desc:
        parts.append(f"({desc})")

    line = indent + " ".join(parts) if any([role, name, value]) else ""
    children_text = ""
    for child in node.get("children", []):
        children_text += _flatten_a11y(child, depth + 1, max_depth)

    return (line + "\n" if line else "") + children_text


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated]"


_JS_INTERACTABLE_ELEMENTS = """
() => {
  const els = document.querySelectorAll(
    'a[href], button, input, select, textarea, [role="button"], [role="link"], [role="menuitem"], [tabindex]'
  );
  return Array.from(els).slice(0, 60).map(el => ({
    tag: el.tagName.toLowerCase(),
    type: el.type || null,
    id: el.id || null,
    name: el.name || null,
    testId: el.getAttribute('data-testid') || null,
    text: (el.innerText || el.value || el.placeholder || '').slice(0, 80).trim(),
    href: el.href || null,
    selector: _getSelector(el),
  }));

  function _getSelector(el) {
    const testId = el.getAttribute('data-testid');
    if (testId) return `[data-testid="${testId}"]`;
    if (el.id) return '#' + el.id;
    if (el.name) return `[name="${el.name}"]`;
    if (el.getAttribute('href')) return `${el.tagName.toLowerCase()}[href="${el.getAttribute('href')}"]`;
    const cls = Array.from(el.classList).slice(0, 2).join('.');
    if (cls) return el.tagName.toLowerCase() + '.' + cls;
    return el.tagName.toLowerCase();
  }
}
"""
