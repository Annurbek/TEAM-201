from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    normalize_phone_number,
    normalize_username,
    verify_password,
)
from app.models.enums import UserRole
from app.models.users import User


class AuthService:
    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
        normalized_username = normalize_username(username)
        result = await db.execute(select(User).where(User.username == normalized_username))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_phone(db: AsyncSession, phone: str) -> Optional[User]:
        normalized_phone = normalize_phone_number(phone)
        result = await db.execute(select(User).where(User.phone == normalized_phone))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(
        db: AsyncSession,
        full_name: str,
        username: str,
        password: str,
        phone: Optional[str] = None,
        role: UserRole = UserRole.student,
    ) -> User:
        username = normalize_username(username)
        phone = normalize_phone_number(phone) if phone else None

        user = User(
            full_name=full_name.strip(),
            username=username,
            phone=phone,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
        user = await AuthService.get_user_by_username(db, username)
        if not user or not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    async def update_last_login(db: AsyncSession, user: User) -> None:
        user.last_login = datetime.utcnow()
        db.add(user)
        await db.commit()
        await db.refresh(user)

    @staticmethod
    def create_access_token_for_user(user: User) -> str:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return create_access_token(
            subject=str(user.id),
            secret_key=settings.SECRET_KEY,
            expires_delta=expires_delta,
        )
