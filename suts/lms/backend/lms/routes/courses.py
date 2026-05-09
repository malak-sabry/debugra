from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lms.db import Course, Enrollment, User, get_session
from lms.auth import get_current_user

router = APIRouter(tags=["courses"])


class CreateCourseRequest(BaseModel):
    title: str
    description: str = ""


@router.post("", status_code=201)
async def create_course(
    body: CreateCourseRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Only teachers can create courses")

    course = Course(
        title=body.title,
        description=body.description,
        teacher_id=current_user.id,
    )
    session.add(course)
    await session.commit()
    await session.refresh(course)
    return {"id": str(course.id), "title": course.title}


@router.get("")
async def list_courses(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(select(Course))
    courses = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "title": c.title,
            "description": c.description,
            "teacher_id": str(c.teacher_id),
        }
        for c in courses
    ]


@router.post("/{course_id}/enroll", status_code=201)
async def enroll(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    course = await session.get(Course, UUID(course_id))
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    existing = await session.execute(
        select(Enrollment).where(
            Enrollment.course_id == UUID(course_id),
            Enrollment.student_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already enrolled")

    enrollment = Enrollment(course_id=UUID(course_id), student_id=current_user.id)
    session.add(enrollment)
    await session.commit()
    return {"enrolled": True, "course_id": course_id}
