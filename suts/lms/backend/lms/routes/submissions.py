from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from lms.db import Submission, User, get_session
from lms.auth import get_current_user

router = APIRouter(tags=["submissions"])


@router.get("")
async def list_my_submissions(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(Submission).where(Submission.student_id == current_user.id)
    )
    submissions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "assignment_id": str(s.assignment_id),
            "score": s.score,
            "feedback": s.feedback,
            "submitted_at": s.submitted_at.isoformat(),
            "graded_at": s.graded_at.isoformat() if s.graded_at else None,
        }
        for s in submissions
    ]


@router.get("/assignment/{assignment_id}")
async def list_assignment_submissions(
    assignment_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Forbidden")

    result = await session.execute(
        select(Submission)
        .options(joinedload(Submission.student))
        .where(Submission.assignment_id == UUID(assignment_id))
    )
    submissions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "student_id": str(s.student_id),
            "student_name": s.student.name,
            "score": s.score,
            "feedback": s.feedback,
            "file_path": s.file_path,
            "text_content": s.text_content,
            "submitted_at": s.submitted_at.isoformat(),
            "graded_at": s.graded_at.isoformat() if s.graded_at else None,
        }
        for s in submissions
    ]
