"""PDF report generation using WeasyPrint + Jinja2."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
)


def _duration_str(started_at: str | None, ended_at: str | None) -> str:
    if not started_at:
        return "—"
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(ended_at) if ended_at else datetime.now(timezone.utc)
        secs = int((end - start).total_seconds())
        if secs < 60:
            return f"{secs}s"
        return f"{secs // 60}m {secs % 60}s"
    except Exception:
        return "—"


def render_report_pdf(
    run: dict[str, Any],
    findings: list[dict[str, Any]],
    agents: list[dict[str, Any]],
    executive_summary: dict[str, Any],
) -> bytes:
    """Render a branded PDF report and return raw bytes."""
    from weasyprint import HTML  # imported lazily — heavy dependency

    agent_durations: dict[str, str] = {
        a["id"]: _duration_str(a.get("started_at"), a.get("ended_at"))
        for a in agents
    }

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    duration = _duration_str(run.get("started_at"), run.get("ended_at"))

    template = _jinja_env.get_template("report.html.j2")
    html_str = template.render(
        run=run,
        findings=findings,
        agents=agents,
        agent_durations=agent_durations,
        executive_summary=executive_summary,
        generated_at=generated_at,
        duration=duration,
    )

    return HTML(string=html_str).write_pdf()
