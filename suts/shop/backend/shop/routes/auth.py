from __future__ import annotations

import os
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shop.db import User, get_session

SECRET_KEY = os.environ.get("SECRET_KEY", "shop-dev-secret-change-me")
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

router = APIRouter(tags=["auth"])


def _hash(pw: str) -> str:
    return pwd_context.hash(pw)


def _verify(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=24)
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid = payload.get("sub")
        if not uid:
            return None
    except JWTError:
        return None
    result = await session.execute(select(User).where(User.id == UUID(uid)))
    return result.scalar_one_or_none()


async def require_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    user = await get_current_user(token, session)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)):
    existing = (await session.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=body.email, hashed_password=_hash(body.password), name=body.name)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return {"access_token": _token(str(user.id)), "token_type": "bearer",
            "user": {"id": str(user.id), "email": user.email, "name": user.name}}


@router.post("/login")
async def login(form: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()
    if not user or not _verify(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": _token(str(user.id)), "token_type": "bearer",
            "user": {"id": str(user.id), "email": user.email, "name": user.name}}
