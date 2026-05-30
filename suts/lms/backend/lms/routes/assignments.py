from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lms.db import Assignment, Course, Submission, User, get_session
from lms.auth import get_current_user

router = APIRouter(tags=["assignments"])

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "./uploads"))
# DEBUGRA_BUG:LMS-01 — No server-side file size validation; only client hint
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB (NOT enforced server-side)


class CreateAssignmentRequest(BaseModel):
    course_id: str
    title: str
    description: str = ""
    max_score: float = 100.0
    due_date: str | None = None


@router.post("", status_code=201)
async def create_assignment(
    body: CreateAssignmentRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # DEBUGRA_BUG:LMS-05 — Teacher can create assignment for any course (no ownership check)
    course = await session.get(Course, UUID(body.course_id))
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    # Missing: if course.teacher_id != current_user.id → 403

    due = None
    if body.due_date:
        try:
            due = datetime.fromisoformat(body.due_date)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid due_date format")

    assignment = Assignment(
        course_id=UUID(body.course_id),
        title=body.title,
        description=body.description,
        max_score=body.max_score,
        due_date=due,
    )
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    return {"id": str(assignment.id), "title": assignment.title}


@router.get("/course/{course_id}")
async def list_assignments(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(Assignment).where(Assignment.course_id == UUID(course_id))
    )
    assignments = result.scalars().all()
    # DEBUGRA_BUG:LMS-07 — Returns empty list with 200 instead of 404 when course doesn't exist
    return [
        {
            "id": str(a.id),
            "title": a.title,
            "description": a.description,
            "max_score": a.max_score,
            "due_date": a.due_date.isoformat() if a.due_date else None,
        }
        for a in assignments
    ]


@router.post("/{assignment_id}/submit", status_code=201)
async def submit_assignment(
    assignment_id: str,
    file: UploadFile = File(None),
    text_content: str = "",
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    assignment = await session.get(Assignment, UUID(assignment_id))
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    file_path = None
    if file and file.filename:
        # DEBUGRA_BUG:LMS-01 — File size not validated; >10MB files accepted
        content = await file.read()
        # Should be: if len(content) > MAX_FILE_SIZE_BYTES: raise HTTPException(413, ...)
        dest = UPLOAD_DIR / f"{assignment_id}_{current_user.id}_{file.filename}"
        dest.write_bytes(content)
        file_path = str(dest)

    # DEBUGRA_BUG:LMS-03 — Race condition: duplicate submissions not prevented
    submission = Submission(
        assignment_id=UUID(assignment_id),
        student_id=current_user.id,
        file_path=file_path,
        text_content=text_content or None,
    )
    session.add(submission)
    await session.commit()
    await session.refresh(submission)
    return {"id": str(submission.id), "submitted_at": submission.submitted_at.isoformat()}


@router.post("/{assignment_id}/grade/{submission_id}")
async def grade_submission(
    assignment_id: str,
    submission_id: str,
    score: float,
    feedback: str = "",
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Only teachers can grade")

    submission = await session.get(Submission, UUID(submission_id))
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    assignment = await session.get(Assignment, UUID(assignment_id))
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # DEBUGRA_BUG:LMS-02 — Off-by-one: score > max_score + 1 instead of >= max_score
    if score > assignment.max_score + 1:
        raise HTTPException(status_code=422, detail=f"Score exceeds max ({assignment.max_score})")

    # DEBUGRA_BUG:LMS-08 — Teacher can grade their own submission (no self-grading prevention)
    submission.score = score
    submission.feedback = feedback
    submission.graded_at = datetime.utcnow()
    await session.commit()
    return {"id": str(submission.id), "score": score}
