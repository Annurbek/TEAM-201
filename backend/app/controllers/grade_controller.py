"""Grade controller — business logic for grade endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AcademicYear, GradeRecord, Semester, User
from app.schemas.edumetric import GradeCreatePayload, GradeUpdatePayload
from app.services.audit_service import log_audit
from app.services.edumetric_service import (
    check_student_access,
    recalculate_and_refresh,
    resolve_scope,
    serialize_model,
)
from app.services.score_service import get_current_semester, get_current_academic_year
from app.models.enums import AuditAction


async def create_grade(
    current_user: User,
    payload: GradeCreatePayload,
    db: AsyncSession,
) -> dict[str, Any]:
    semester, academic_year = await resolve_scope(db, payload.semester_id)
    grade = GradeRecord(
        student_id=payload.student_id,
        course_id=payload.course_id,
        semester_id=semester.id,
        assignment_name=payload.assignment_name,
        score=payload.score,
        max_score=payload.max_score,
        submission_date=payload.submission_date,
        deadline=payload.deadline,
        is_late=payload.is_late,
        quality=payload.quality,
        is_independent=payload.is_independent,
        graded_by_id=current_user.id,
    )
    db.add(grade)
    await db.commit()
    await recalculate_and_refresh(
        db, payload.student_id, semester.id, academic_year.id,
        actor_id=current_user.id, reason="grade added",
    )
    await log_audit(
        db, actor_id=current_user.id, action=AuditAction.create, model_name="GradeRecord",
        record_id=grade.id, request_path="/grades", request_method="POST",
        new_data=payload.model_dump(),
    )
    return {"id": grade.id, "message": "Grade recorded"}


async def list_grades(
    current_user: User,
    student_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    await check_student_access(current_user, student_id, db)
    result = await db.execute(select(GradeRecord).where(GradeRecord.student_id == student_id).order_by(GradeRecord.created_at.desc()))
    return {"items": [serialize_model(record) for record in result.scalars().all()]}


async def update_grade(
    grade_id: int,
    payload: GradeUpdatePayload,
    current_user: User,
    db: AsyncSession,
) -> dict[str, Any]:
    result = await db.execute(select(GradeRecord).where(GradeRecord.id == grade_id))
    grade = result.scalar_one_or_none()
    if grade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade not found")
    old_student_id = grade.student_id
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(grade, field, value)
    db.add(grade)
    await db.commit()
    semester, academic_year = await resolve_scope(db, grade.semester_id)
    await recalculate_and_refresh(
        db, old_student_id, semester.id, academic_year.id,
        actor_id=current_user.id, reason="grade updated",
    )
    return {"message": "Grade updated"}


async def delete_grade(
    grade_id: int,
    current_user: User,
    db: AsyncSession,
) -> dict[str, Any]:
    result = await db.execute(select(GradeRecord).where(GradeRecord.id == grade_id))
    grade = result.scalar_one_or_none()
    if grade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade not found")
    student_id = grade.student_id
    semester, academic_year = await resolve_scope(db, grade.semester_id)
    await db.delete(grade)
    await db.commit()
    await recalculate_and_refresh(
        db, student_id, semester.id, academic_year.id,
        actor_id=current_user.id, reason="grade deleted",
    )
    return {"message": "Grade deleted"}


async def grade_stats(
    current_user: User,
    student_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    await check_student_access(current_user, student_id, db)
    result = await db.execute(
        select(func.coalesce(func.avg((GradeRecord.score / func.nullif(GradeRecord.max_score, 0)) * 100), 0.0))
        .where(GradeRecord.student_id == student_id)
    )
    return {"average_percentage": float(result.scalar_one() or 0.0)}
