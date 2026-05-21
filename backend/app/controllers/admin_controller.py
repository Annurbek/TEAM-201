"""Admin controller — business logic for admin endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AcademicYear,
    AuditLog,
    Group,
    RankingSnapshot,
    Semester,
    Semester,
    StudentProfile,
    User,
)
from app.schemas.user import UserCreatePayload
from app.schemas.edumetric import NotificationPayload
from app.services.auth_service import AuthService
from app.services.audit_service import log_audit
from app.services.edumetric_service import (
    recalculate_and_refresh,
    serialize_model,
    serialize_user,
)
from app.services.notification_service import create_notification
from app.services.score_service import (
    get_current_academic_year,
    get_current_semester,
    get_year_leaderboard,
)
from app.models.enums import AuditAction


async def admin_dashboard(
    db: AsyncSession,
) -> dict[str, Any]:
    total_students = (await db.execute(select(func.count()).select_from(StudentProfile))).scalar_one()
    grant_eligible = (await db.execute(select(func.count()).select_from(RankingSnapshot).where(RankingSnapshot.total_points >= 80))).scalar_one()
    avg_score = (await db.execute(select(func.coalesce(func.avg(RankingSnapshot.total_points), 0.0)))).scalar_one()
    return {"total_students": total_students, "grant_eligible": grant_eligible, "average_score": float(avg_score or 0.0)}


async def audit_log(
    db: AsyncSession,
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    result = await db.execute(query.offset((page - 1) * size).limit(size))
    return {"items": [serialize_model(record) for record in result.scalars().all()], "page": page, "size": size, "total": total}


async def admin_create_user(
    current_user: User,
    payload: UserCreatePayload,
    db: AsyncSession,
) -> dict[str, Any]:
    user, username, password = await AuthService.provision_admin_user(
        db=db,
        full_name=payload.full_name,
        role=payload.role,
        username=payload.username,
        password=payload.password,
        phone=payload.phone,
        student_code=payload.student_code,
        group_id=payload.current_group_id,
        academic_year_id=payload.admission_year,
    )
    response = serialize_user(user)
    response["generated_password"] = password
    response["generated_username"] = username
    await log_audit(
        db, actor_id=current_user.id, action=AuditAction.create, model_name="User",
        record_id=user.id, request_path="/admin/users", request_method="POST",
        new_data={**payload.model_dump(), "username": username},
    )
    return response


async def admin_toggle_user(
    user_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = not user.is_active
    db.add(user)
    await db.commit()
    return serialize_user(user)


async def grant_report(
    db: AsyncSession,
) -> dict[str, Any]:
    academic_year = await get_current_academic_year(db)
    if academic_year is None:
        return {"items": []}
    leaderboard = await get_year_leaderboard(db, academic_year.id)
    return {"items": leaderboard}


async def recalculate_all(
    current_user: User,
    db: AsyncSession,
) -> dict[str, Any]:
    semester = await get_current_semester(db)
    academic_year = await get_current_academic_year(db)
    if semester is None or academic_year is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current scope not available")
    result = await db.execute(select(StudentProfile.id))
    student_ids = [row[0] for row in result.all()]
    for student_id in student_ids:
        await recalculate_and_refresh(
            db, student_id, semester.id, academic_year.id,
            actor_id=current_user.id, reason="bulk recalculation",
        )
    return {"recalculated": len(student_ids)}


async def send_notification(
    payload: NotificationPayload,
    db: AsyncSession,
) -> dict[str, Any]:
    notification = await create_notification(
        db, user_id=payload.user_id, title=payload.title,
        message=payload.message, notification_type=payload.type,
    )
    return {"id": notification.id, "message": "Notification sent"}
