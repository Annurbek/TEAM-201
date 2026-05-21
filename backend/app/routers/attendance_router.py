"""Attendance router — endpoint definitions for attendance management."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_role
from app.core.security import get_current_user
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.users import User
from app.schemas.edumetric import AttendanceCreatePayload, AttendanceBulkPayload
from app.controllers.attendance_controller import (
    list_attendance,
    course_attendance,
    attendance_stats,
    create_attendance,
    bulk_attendance,
    update_attendance,
)

router = APIRouter(tags=["Attendance"])


@router.get("/attendance/{student_id}")
async def list_attendance_endpoint(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    course_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    return await list_attendance(current_user, student_id, db, course_id=course_id, date_from=date_from, date_to=date_to)


@router.get("/attendance/course/{course_id}")
async def course_attendance_endpoint(
    course_id: int,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await course_attendance(course_id, db)


@router.get("/attendance/stats/{student_id}")
async def attendance_stats_endpoint(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await attendance_stats(current_user, student_id, db)


@router.post("/attendance")
async def create_attendance_endpoint(
    payload: AttendanceCreatePayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await create_attendance(current_user, payload, db)


@router.post("/attendance/bulk")
async def bulk_attendance_endpoint(
    payload: AttendanceBulkPayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await bulk_attendance(current_user, payload, db)


@router.put("/attendance/{attendance_id}")
async def update_attendance_endpoint(
    attendance_id: int,
    payload: AttendanceCreatePayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await update_attendance(attendance_id, payload, current_user, db)
