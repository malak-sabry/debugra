from __future__ import annotations

import os
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://lms:lms@localhost:5433/lms",
)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with async_session_maker() as session:
        yield session


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # teacher | student | admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    courses_taught: Mapped[list[Course]] = relationship("Course", back_populates="teacher", foreign_keys="Course.teacher_id")
    enrollments: Mapped[list[Enrollment]] = relationship("Enrollment", back_populates="student")
    submissions: Mapped[list[Submission]] = relationship("Submission", back_populates="student")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    teacher_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    teacher: Mapped[User] = relationship("User", back_populates="courses_taught", foreign_keys=[teacher_id])
    assignments: Mapped[list[Assignment]] = relationship("Assignment", back_populates="course")
    enrollments: Mapped[list[Enrollment]] = relationship("Enrollment", back_populates="course")


class Enrollment(Base):
    __tablename__ = "enrollments"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("courses.id"))
    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    enrolled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    course: Mapped[Course] = relationship("Course", back_populates="enrollments")
    student: Mapped[User] = relationship("User", back_populates="enrollments")


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("courses.id"))
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    max_score: Mapped[float] = mapped_column(Float, default=100.0)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    course: Mapped[Course] = relationship("Course", back_populates="assignments")
    submissions: Mapped[list[Submission]] = relationship("Submission", back_populates="assignment")


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    assignment_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("assignments.id"))
    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    assignment: Mapped[Assignment] = relationship("Assignment", back_populates="submissions")
    student: Mapped[User] = relationship("User", back_populates="submissions")


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
