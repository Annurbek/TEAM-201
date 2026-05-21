"""Employment controller — business logic for employment endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EmploymentRecord, Semester, StudentProfile, User
from app.schemas.edumetric import EmploymentPayload
from app.services.edumetric_service import (
    get_student_profile_or_404,
    recalculate_and_refresh,
    resolve_scope,
    serialize_model,
)
from app.services.score_service import get_current_semester, get_current_academic_year, clamp


async def create_employment(
    current_user: User,
    payload: EmploymentPayload,
    document_url: str | None,
    db: AsyncSession,
) -> dict[str, Any]:
    student = await get_student_profile_or_404(db, current_user.id if current_user.role == "student" else payload.student_id)
    employment = EmploymentRecord(
        student_id=student.id,
        company_name=payload.company_name,
        position=payload.position,
        type=payload.type.value,
        hours_per_week=payload.hours_per_week,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_it_related=payload.is_it_related,
        bonus_points=clamp(payload.bonus_points, 0.0, 10.0),
        verified=False,
        document_url=document_url,
        semester_id=payload.semester_id,
        semester=payload.semester,
        year=payload.year,
    )
    db.add(employment)
    await db.commit()
    return {"id": employment.id, "message": "Employment submitted"}


async def my_employment(
    current_user: User,
    db: AsyncSession,
) -> dict[str, Any]:
    student = await get_student_profile_or_404(db, current_user.id)
    result = await db.execute(select(EmploymentRecord).where(EmploymentRecord.student_id == student.id).order_by(EmploymentRecord.created_at.desc()))
    return {"items": [serialize_model(record) for record in result.scalars().all()]}


async def list_employment(
    db: AsyncSession,
) -> dict[str, Any]:
    result = await db.execute(select(EmploymentRecord).order_by(EmploymentRecord.created_at.desc()))
    return {"items": [record.__dict__ for record in result.scalars().all()]}


async def verify_employment(
    employment_id: int,
    bonus_points: float,
    current_user: User,
    db: AsyncSession,
) -> dict[str, Any]:
    result = await db.execute(select(EmploymentRecord).where(EmploymentRecord.id == employment_id))
    employment = result.scalar_one_or_none()
    if employment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employment not found")
    employment.verified = True
    employment.bonus_points = clamp(bonus_points, 0.0, 10.0)
    db.add(employment)
    await db.commit()
    semester, academic_year = await resolve_scope(db, employment.semester_id)
    await recalculate_and_refresh(
        db, employment.student_id, semester.id, academic_year.id,
        actor_id=current_user.id, reason="employment verified",
    )
    return {"message": "Employment verified"}
