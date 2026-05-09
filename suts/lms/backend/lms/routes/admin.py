from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from lms.db import User, Course, Assignment, Submission, get_session
from lms.auth import get_current_user

router = APIRouter(tags=["admin"])


@router.get("/dashboard")
async def dashboard(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    user_count = (await session.execute(select(func.count(User.id)))).scalar()
    course_count = (await session.execute(select(func.count(Course.id)))).scalar()
    submission_count = (await session.execute(select(func.count(Submission.id)))).scalar()

    # DEBUGRA_BUG:LMS-06 — Stale cache: analytics not refreshed after new enrollments
    # (in real app this would be a cached value; for demo it's just computed freshly but
    # the UI shows a "Last updated" timestamp that never changes — seeded in frontend)

    return {
        "users": user_count,
        "courses": course_count,
        "submissions": submission_count,
        "revenue": 0,
    }


@router.get("/users")
async def list_users(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    result = await session.execute(select(User))
    users = result.scalars().all()
    return [
        {"id": str(u.id), "email": u.email, "name": u.name, "role": u.role, "is_active": u.is_active}
        for u in users
    ]
