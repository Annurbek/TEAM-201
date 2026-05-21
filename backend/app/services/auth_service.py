from __future__ import annotations

from datetime import datetime, timedelta
from secrets import choice
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
from app.models.student import StudentProfile
from app.models.parent import ParentProfile
from app.models.tutor import TutorProfile
from app.models.groups import Group
from app.models.academic_year import AcademicYear


class AuthService:
    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
        normalized_username = normalize_username(username)
        result = await db.execute(select(User).where(User.username == normalized_username))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        return await AuthService.get_user_by_username(db, email)

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
    def generate_username(full_name: str) -> str:
        normalized = "".join(ch.lower() if ch.isalnum() else "-" for ch in full_name.strip())
        normalized = "-".join(part for part in normalized.split("-") if part)
        return normalized or f"user-{int(datetime.utcnow().timestamp())}"

    @staticmethod
    async def get_available_username(db: AsyncSession, base_username: str) -> str:
        candidate = normalize_username(base_username)
        suffix = 1
        while True:
            result = await db.execute(select(User.id).where(User.username == candidate))
            if result.scalar_one_or_none() is None:
                return candidate
            suffix += 1
            max_base_length = 255 - len(f"-{suffix}")
            candidate = f"{normalize_username(base_username)[:max_base_length]}-{suffix}"

    @staticmethod
    def generate_password(length: int = 12) -> str:
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%"
        return "".join(choice(alphabet) for _ in range(length))

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
    async def register_user(
        db: AsyncSession,
        full_name: str,
        username: str,
        password: str,
        role: UserRole,
        phone: Optional[str] = None,
        student_code: Optional[str] = None,
        group_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
    ) -> User:
        existing = await AuthService.get_user_by_username(db, username)
        if existing:
            raise ValueError("User with this username already exists")

        user = await AuthService.create_user(
            db=db,
            full_name=full_name,
            username=username,
            password=password,
            phone=phone,
            role=role,
        )

        if role == UserRole.student:
            student_profile = StudentProfile(
                user_id=user.id,
                student_code=student_code,
                current_group_id=group_id,
                admission_year=academic_year_id,
            )
            db.add(student_profile)
        elif role == UserRole.parent:
            db.add(ParentProfile(user_id=user.id))
        elif role in {UserRole.tutor, UserRole.super_admin, UserRole.admin}:
            if role == UserRole.tutor:
                db.add(TutorProfile(user_id=user.id))

        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def provision_admin_user(
        db: AsyncSession,
        full_name: str,
        role: UserRole,
        username: Optional[str] = None,
        password: Optional[str] = None,
        phone: Optional[str] = None,
        student_code: Optional[str] = None,
        group_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
    ) -> tuple[User, str, str]:
        raw_username = username.strip().lower() if username else AuthService.generate_username(full_name)
        available_username = await AuthService.get_available_username(db, raw_username)
        generated_password = password or AuthService.generate_password()

        user = await AuthService.create_user(
            db=db,
            full_name=full_name,
            username=available_username,
            password=generated_password,
            phone=phone,
            role=role,
        )

        if role == UserRole.student:
            db.add(
                StudentProfile(
                    user_id=user.id,
                    student_code=student_code,
                    current_group_id=group_id,
                    admission_year=academic_year_id,
                )
            )
        elif role == UserRole.parent:
            db.add(ParentProfile(user_id=user.id))
        elif role == UserRole.tutor:
            db.add(TutorProfile(user_id=user.id))

        await db.commit()
        await db.refresh(user)
        return user, available_username, generated_password

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

    @staticmethod
    async def update_profile(
        db: AsyncSession,
        user: User,
        full_name: Optional[str] = None,
        phone: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> User:
        if full_name is not None:
            user.full_name = full_name.strip()
        if phone is not None:
            user.phone = normalize_phone_number(phone) if phone else None
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def change_password(
        db: AsyncSession,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        if not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is invalid")
        user.password_hash = hash_password(new_password)
        db.add(user)
        await db.commit()
        await db.refresh(user)
