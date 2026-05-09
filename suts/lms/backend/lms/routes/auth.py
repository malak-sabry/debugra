from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lms.db import User, get_session
from lms.auth import hash_password, verify_password, create_access_token

router = APIRouter(tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "student"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)):
    existing = await session.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        name=body.name,
        role=body.role if body.role in ("student", "teacher", "admin") else "student",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user={"id": str(user.id), "email": user.email, "name": user.name, "role": user.role},
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user={"id": str(user.id), "email": user.email, "name": user.name, "role": user.role},
    )


@router.get("/me")
async def me(session: AsyncSession = Depends(get_session), token: str = ""):
    from lms.auth import get_current_user
    return {"message": "Use Authorization header"}


# DEBUGRA_BUG:LMS-09 — Password reset token can be reused indefinitely
# The reset token is never invalidated after first use, allowing replay attacks.
# Fix: mark token as used / delete after successful password change.

_reset_tokens: dict[str, str] = {}  # email → token (never cleared after use)


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


@router.post("/password-reset/request", status_code=202)
async def request_password_reset(body: PasswordResetRequest, session: AsyncSession = Depends(get_session)):
    import secrets
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user:
        return {"message": "If that email exists, a reset link was sent"}
    token = secrets.token_urlsafe(32)
    _reset_tokens[body.email] = token  # DEBUGRA_BUG:LMS-09 — stored but never expires
    return {"message": "If that email exists, a reset link was sent", "debug_token": token}


@router.post("/password-reset/confirm")
async def confirm_password_reset(body: PasswordResetConfirm, session: AsyncSession = Depends(get_session)):
    email = next((e for e, t in _reset_tokens.items() if t == body.token), None)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(body.new_password)
    # DEBUGRA_BUG:LMS-09 — Missing: del _reset_tokens[email]
    # Token remains valid → can be reused to reset password again
    await session.commit()
    return {"message": "Password updated successfully"}
