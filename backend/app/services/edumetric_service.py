"""Shared helpers for edumetric controllers."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AcademicYear,
    Group,
    ParentProfile,
    RankingSnapshot,
    Semester,
    StudentParentLink,
    StudentProfile,
    User,
    UserRole,
)
from app.services.score_service import (
    calculate_student_score,
    get_current_academic_year,
    get_current_semester,
    recalculate_rankings,
)


async def resolve_scope(
    db: AsyncSession,
    semester_id: int | None = None,
    academic_year_id: int | None = None,
) -> tuple[Semester, AcademicYear]:
    semester = None
    academic_year = None
    if semester_id is None:
        semester = await get_current_semester(db)
    else:
        semester = (await db.execute(select(Semester).where(Semester.id == semester_id))).scalar_one_or_none()
    if semester is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semester not found")

    if academic_year_id is None:
        academic_year = (await db.execute(select(AcademicYear).where(AcademicYear.id == semester.academic_year_id))).scalar_one_or_none()
    else:
        academic_year = (await db.execute(select(AcademicYear).where(AcademicYear.id == academic_year_id))).scalar_one_or_none()
    if academic_year is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")
    return semester, academic_year


async def get_student_profile_or_404(db: AsyncSession, student_id: int) -> StudentProfile:
    result = await db.execute(select(StudentProfile).where(StudentProfile.id == student_id))
    student = result.scalar_one_or_none()
    if student is not None:
        return student
    result = await db.execute(select(StudentProfile).where(StudentProfile.user_id == student_id))
    student = result.scalar_one_or_none()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


async def check_student_access(current_user: User, student_id: int, db: AsyncSession) -> StudentProfile:
    student = await get_student_profile_or_404(db, student_id)
    if current_user.role in {UserRole.admin, UserRole.super_admin, UserRole.tutor, UserRole.mentor}:
        return student
    if current_user.role == UserRole.student and student.user_id == current_user.id:
        return student
    if current_user.role == UserRole.parent:
        result = await db.execute(select(ParentProfile).where(ParentProfile.user_id == current_user.id))
        parent = result.scalar_one_or_none()
        if parent is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        link_result = await db.execute(
            select(StudentParentLink).where(
                StudentParentLink.student_id == student.id,
                StudentParentLink.parent_id == parent.id,
                StudentParentLink.is_active.is_(True),
            )
        )
        link = link_result.scalar_one_or_none()
        if link is not None:
            return student
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


async def recalculate_and_refresh(
    db: AsyncSession,
    student_id: int,
    semester_id: int,
    academic_year_id: int,
    actor_id: int | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    score = await calculate_student_score(
        db,
        student_id=student_id,
        semester_id=semester_id,
        academic_year_id=academic_year_id,
        actor_id=actor_id,
        reason=reason,
    )
    await recalculate_rankings(db, semester_id=semester_id, academic_year_id=academic_year_id)
    return score


def serialize_user(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "full_name": user.full_name,
        "username": user.username,
        "phone": user.phone,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "last_login": user.last_login,
    }


def serialize_model(instance: Any) -> dict[str, Any]:
    return {key: value for key, value in instance.__dict__.items() if not key.startswith("_sa_")}
