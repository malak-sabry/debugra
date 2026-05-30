from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from orchestrator.config import get_settings

router = APIRouter(prefix="/artifacts", tags=["artifacts"])
settings = get_settings()


@router.get("/{artifact_path:path}")
async def get_artifact(artifact_path: str) -> FileResponse:
    base_dir = Path(settings.artifacts_dir).resolve()
    raw_path = unquote(artifact_path)

    candidates: list[Path] = []
    requested = Path(raw_path)
    if requested.is_absolute():
        candidates.append(requested)
    else:
        clean_path = raw_path.removeprefix("runs/").lstrip("/")
        candidates.append(base_dir / clean_path)
        candidates.append(base_dir.parent / raw_path)

    for candidate in candidates:
        resolved = candidate.resolve()
        try:
            resolved.relative_to(base_dir)
        except ValueError:
            continue
        if resolved.is_file():
            return FileResponse(resolved)

    raise HTTPException(status_code=404, detail="Artifact not found")
