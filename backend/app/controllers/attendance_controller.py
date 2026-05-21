"""Attendance controller — business logic for attendance endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AcademicYear,
    AttendanceRecord,
    AttendanceScore,
    Semester,
    User,
)
from app.schemas.edumetric import AttendanceCreatePayload, AttendanceBulkPayload
from app.services.audit_service import log_audit
from app.services.edumetric_service import (
    check_student_access,
    recalculate_and_refresh,
    resolve_scope,
    serialize_model,
)
from app.services.notification_service import create_notification
from app.services.score_service import get_current_semester
from app.models.edumetric import NotificationType
from app.models.enums import AuditAction
from app.controllers.student_controller import get_student_profile_or_404


async def list_attendance(
    current_user: User,
    student_id: int,
    db: AsyncSession,
    course_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    await check_student_access(current_user, student_id, db)
    query = select(AttendanceRecord).where(AttendanceRecord.student_id == student_id)
    if course_id is not None:
        query = query.where(AttendanceRecord.course_id == course_id)
    if date_from is not None:
        query = query.where(AttendanceRecord.date >= date_from)
    if date_to is not None:
        query = query.where(AttendanceRecord.date <= date_to)
    result = await db.execute(query.order_by(AttendanceRecord.date.desc()))
    return {"items": [serialize_model(record) for record in result.scalars().all()]}


async def course_attendance(
    course_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    result = await db.execute(select(AttendanceRecord).where(AttendanceRecord.course_id == course_id).order_by(AttendanceRecord.date.desc()))
    return {"items": [serialize_model(record) for record in result.scalars().all()]}


async def attendance_stats(
    current_user: User,
    student_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    await check_student_access(current_user, student_id, db)
    semester = await get_current_semester(db)
    if semester is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semester not found")
    result = await db.execute(select(AttendanceScore).where(AttendanceScore.student_id == student_id, AttendanceScore.semester_id == semester.id))
    score = result.scalar_one_or_none()
    return {"percent": 0.0 if score is None else score.percent, "points": 0.0 if score is None else score.points}


async def create_attendance(
    current_user: User,
    payload: AttendanceCreatePayload,
    db: AsyncSession,
) -> dict[str, Any]:
    semester, academic_year = await resolve_scope(db, payload.semester_id)
    attendance = AttendanceRecord(
        student_id=payload.student_id,
        course_id=payload.course_id,
        semester_id=semester.id,
        date=payload.date,
        status=payload.status,
        recorded_by_id=current_user.id,
        note=payload.note,
    )
    db.add(attendance)
    await db.commit()
    await recalculate_and_refresh(
        db, payload.student_id, semester.id, academic_year.id,
        actor_id=current_user.id, reason="attendance marked",
    )
    await log_audit(
        db, actor_id=current_user.id, action=AuditAction.create, model_name="AttendanceRecord",
        record_id=attendance.id, request_path="/attendance", request_method="POST",
        new_data=payload.model_dump(),
    )
    student = await get_student_profile_or_404(db, payload.student_id)
    await create_notification(
        db, user_id=student.user_id, title="Attendance updated",
        message=f"Attendance recorded for {payload.date}", notification_type=NotificationType.info,
    )
    return {"id": attendance.id, "message": "Attendance recorded"}


async def bulk_attendance(
    current_user: User,
    payload: AttendanceBulkPayload,
    db: AsyncSession,
) -> dict[str, Any]:
    from app.models.edumetric import AttendanceStatus

    semester, academic_year = await resolve_scope(db, payload.semester_id)
    created: list[int] = []
    for record in payload.records:
        attendance = AttendanceRecord(
            student_id=int(record["student_id"]),
            course_id=payload.course_id,
            semester_id=semester.id,
            date=payload.date,
            status=AttendanceStatus(record["status"]),
            recorded_by_id=current_user.id,
        )
        db.add(attendance)
        await db.flush()
        created.append(attendance.id)
        await recalculate_and_refresh(
            db, attendance.student_id, semester.id, academic_year.id,
            actor_id=current_user.id, reason="bulk attendance",
        )
    await db.commit()
    return {"created": created}


async def update_attendance(
    attendance_id: int,
    payload: AttendanceCreatePayload,
    current_user: User,
    db: AsyncSession,
) -> dict[str, Any]:
    result = await db.execute(select(AttendanceRecord).where(AttendanceRecord.id == attendance_id))
    attendance = result.scalar_one_or_none()
    if attendance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance not found")
    old = serialize_model(attendance)
    attendance.student_id = payload.student_id
    attendance.course_id = payload.course_id
    attendance.date = payload.date
    attendance.status = payload.status
    attendance.note = payload.note
    db.add(attendance)
    await db.commit()
    semester, academic_year = await resolve_scope(db, attendance.semester_id)
    await recalculate_and_refresh(
        db, attendance.student_id, semester.id, academic_year.id,
        actor_id=current_user.id, reason="attendance updated",
    )
    await log_audit(
        db, actor_id=current_user.id, action=AuditAction.update, model_name="AttendanceRecord",
        record_id=attendance.id, request_path=f"/attendance/{attendance_id}", request_method="PUT",
        old_data=old, new_data=payload.model_dump(),
    )
    return {"message": "Attendance updated"}
