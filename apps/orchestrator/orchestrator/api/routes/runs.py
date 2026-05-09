from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from debugra_schemas import Run, RunStatus, SUT
from orchestrator.db import RunModel, FindingModel, AgentModel, get_session
from orchestrator.graph import build_run_graph, RunState
from orchestrator.event_bus import publish_event

router = APIRouter(prefix="/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    sut: SUT
    readme: str = ""
    config: dict[str, Any] = {}


class CreateRunResponse(BaseModel):
    run_id: str
    status: RunStatus


@router.post("", response_model=CreateRunResponse, status_code=201)
async def create_run(
    body: CreateRunRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    run_id = uuid4()

    db_run = RunModel(
        id=run_id,
        sut=body.sut,
        status=RunStatus.PENDING,
        config=body.config,
        created_at=datetime.now(timezone.utc),
    )
    session.add(db_run)
    await session.commit()

    background_tasks.add_task(
        _execute_run,
        run_id=str(run_id),
        sut=body.sut,
        readme=body.readme,
    )

    return CreateRunResponse(run_id=str(run_id), status=RunStatus.PENDING)


@router.get("", response_model=list[dict])
async def list_runs(session: AsyncSession = Depends(get_session)):
    from sqlalchemy import select
    result = await session.execute(select(RunModel).order_by(RunModel.created_at.desc()).limit(50))
    runs = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "sut": r.sut,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "ended_at": r.ended_at.isoformat() if r.ended_at else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]


@router.get("/{run_id}", response_model=dict)
async def get_run(run_id: UUID, session: AsyncSession = Depends(get_session)):
    from sqlalchemy import select
    result = await session.execute(select(RunModel).where(RunModel.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "id": str(run.id),
        "sut": run.sut,
        "status": run.status,
        "plan": run.plan,
        "config": run.config,
        "artifact_dir": run.artifact_dir,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "ended_at": run.ended_at.isoformat() if run.ended_at else None,
        "created_at": run.created_at.isoformat(),
    }


@router.get("/{run_id}/findings", response_model=list[dict])
async def get_findings(run_id: UUID, session: AsyncSession = Depends(get_session)):
    from sqlalchemy import select
    result = await session.execute(
        select(FindingModel).where(FindingModel.run_id == run_id).order_by(FindingModel.detected_at)
    )
    findings = result.scalars().all()
    return [
        {
            "id": str(f.id),
            "severity": f.severity,
            "title": f.title,
            "description": f.description,
            "repro_steps": f.repro_steps,
            "evidence_paths": f.evidence_paths,
            "oracle_type": f.oracle_type,
            "ground_truth_bug_id": f.ground_truth_bug_id,
            "detected_at": f.detected_at.isoformat(),
        }
        for f in findings
    ]


@router.get("/{run_id}/agents", response_model=list[dict])
async def get_agents(run_id: UUID, session: AsyncSession = Depends(get_session)):
    from sqlalchemy import select
    result = await session.execute(
        select(AgentModel).where(AgentModel.run_id == run_id)
    )
    agents = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "role": a.role,
            "status": a.status,
            "step_count": a.step_count,
            "trace_path": a.trace_path,
            "started_at": a.started_at.isoformat() if a.started_at else None,
            "ended_at": a.ended_at.isoformat() if a.ended_at else None,
        }
        for a in agents
    ]


@router.get("/{run_id}/report.pdf")
async def get_report_pdf(run_id: UUID, session: AsyncSession = Depends(get_session)):
    from sqlalchemy import select
    from orchestrator.pdf import render_report_pdf

    run = await session.get(RunModel, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    findings_result = await session.execute(
        select(FindingModel).where(FindingModel.run_id == run_id).order_by(FindingModel.detected_at)
    )
    findings = findings_result.scalars().all()

    agents_result = await session.execute(
        select(AgentModel).where(AgentModel.run_id == run_id)
    )
    agents = agents_result.scalars().all()

    run_dict = {
        "id": str(run.id),
        "sut": run.sut,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "ended_at": run.ended_at.isoformat() if run.ended_at else None,
        "created_at": run.created_at.isoformat(),
    }
    findings_list = [
        {
            "id": str(f.id),
            "severity": f.severity,
            "title": f.title,
            "description": f.description,
            "repro_steps": f.repro_steps or [],
            "evidence_paths": f.evidence_paths or [],
            "oracle_type": f.oracle_type,
            "ground_truth_bug_id": f.ground_truth_bug_id,
        }
        for f in findings
    ]
    agents_list = [
        {
            "id": str(a.id),
            "role": a.role,
            "status": a.status,
            "step_count": a.step_count,
            "started_at": a.started_at.isoformat() if a.started_at else None,
            "ended_at": a.ended_at.isoformat() if a.ended_at else None,
        }
        for a in agents
    ]

    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings_list:
        sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1

    critical_high = [f for f in findings_list if f["severity"] in ("critical", "high")]
    executive_summary = {
        "headline": (
            f"Debugra detected {len(findings_list)} issue(s) during autonomous testing of {run.sut.upper()}."
            if findings_list
            else f"No issues detected during autonomous testing of {run.sut.upper()}."
        ),
        "top_risks": [f["title"] for f in critical_high[:5]],
        "coverage_summary": (
            f"{len(agents_list)} agent(s) executed a total of "
            f"{sum(a['step_count'] for a in agents_list)} steps across the {run.sut.upper()} SUT."
        ),
        "benchmark_note": run.plan.get("benchmark_note") if run.plan else None,
    }

    try:
        pdf_bytes = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: render_report_pdf(run_dict, findings_list, agents_list, executive_summary),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF render failed: {exc}") from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="debugra-report-{str(run_id)[:8]}.pdf"'},
    )


# ─── Background task ──────────────────────────────────────────────────────────


async def _execute_run(run_id: str, sut: SUT, readme: str) -> None:
    from orchestrator.db import async_session_maker
    from debugra_schemas import RunEventType

    graph = build_run_graph()

    async def event_callback(event_type: RunEventType, payload: dict) -> None:
        await publish_event(run_id, event_type, payload)

    sut_urls = {
        SUT.LMS: "http://localhost:3001",
        SUT.SHOP: "http://localhost:3002",
    }

    state: RunState = {
        "run_id": run_id,
        "sut": sut,
        "base_url": sut_urls.get(sut, "http://localhost:3001"),
        "readme_content": readme,
        "plan": None,
        "agent_results": [],
        "findings": [],
        "report": None,
        "error": None,
        "event_callback": event_callback,
    }

    async with async_session_maker() as session:
        db_run = await session.get(RunModel, run_id)
        if db_run:
            db_run.status = RunStatus.PLANNING
            db_run.started_at = datetime.now(timezone.utc)
            await session.commit()

    await publish_event(run_id, RunEventType.RUN_STARTED, {"sut": sut, "run_id": run_id})

    try:
        final_state = await graph.ainvoke(state)

        async with async_session_maker() as session:
            db_run = await session.get(RunModel, run_id)
            if db_run:
                db_run.status = RunStatus.COMPLETE if not final_state.get("error") else RunStatus.FAILED
                db_run.ended_at = datetime.now(timezone.utc)
                db_run.plan = final_state.get("plan")
                await session.commit()

        event_type = RunEventType.RUN_COMPLETE if not final_state.get("error") else RunEventType.RUN_FAILED
        await publish_event(run_id, event_type, {"error": final_state.get("error")})

    except Exception as exc:
        async with async_session_maker() as session:
            db_run = await session.get(RunModel, run_id)
            if db_run:
                db_run.status = RunStatus.FAILED
                db_run.ended_at = datetime.now(timezone.utc)
                await session.commit()
        await publish_event(run_id, RunEventType.RUN_FAILED, {"error": str(exc)})
