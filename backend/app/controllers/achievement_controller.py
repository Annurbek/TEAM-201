"""Achievement controller — business logic for achievement endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AchievementApplication,
    AchievementStatus,
    AchievementType,
    Semester,
    StudentProfile,
    User,
)
from app.schemas.edumetric import AchievementReviewPayload
from app.services.audit_service import log_audit
from app.services.edumetric_service import (
    get_student_profile_or_404,
    recalculate_and_refresh,
    resolve_scope,
    serialize_model,
)
from app.services.score_service import get_current_semester, get_current_academic_year
from app.models.enums import AuditAction

ACHIEVEMENT_LIMITS = {
    AchievementType.hackathon_participant: 1,
    AchievementType.hackathon_winner: 3,
    AchievementType.startup: 7,
    AchievementType.mentoring: 3,
    AchievementType.certificate_online: 2,
    AchievementType.certificate_offline: 3,
    AchievementType.certificate_national_it: 2,
    AchievementType.certificate_language: 5,
    AchievementType.certificate_international: 10,
    AchievementType.volunteering: 2,
    AchievementType.soft_skills: 1,
    AchievementType.networking: 1,
    AchievementType.project_participant: 2,
    AchievementType.direction_assistant: 3,
    AchievementType.strategic_assistant: 4,
}


def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(value, max_val))


async def submit_achievement(
    current_user: User,
    achievement_type: AchievementType,
    title: str,
    description: str | None,
    points_claimed: float,
    semester_id: int | None,
    document_url: str | None,
    db: AsyncSession,
) -> dict[str, Any]:
    semester, academic_year = await resolve_scope(db, semester_id)
    student = await get_student_profile_or_404(db, current_user.id)
    achievement = AchievementApplication(
        student_id=student.id,
        semester_id=semester.id,
        type=achievement_type,
        title=title,
        description=description,
        document_url=document_url,
        points_claimed=points_claimed,
        status=AchievementStatus.pending,
    )
    db.add(achievement)
    await db.commit()
    await log_audit(
        db, actor_id=current_user.id, action=AuditAction.create, model_name="AchievementApplication",
        record_id=achievement.id, request_path="/achievements", request_method="POST",
        new_data={"title": title, "type": achievement_type.value},
    )
    return {"id": achievement.id, "message": "Achievement submitted"}


async def list_achievements(
    db: AsyncSession,
    status_filter: AchievementStatus | None = None,
    type_filter: AchievementType | None = None,
    student_id: int | None = None,
) -> dict[str, Any]:
    query = select(AchievementApplication)
    if status_filter is not None:
        query = query.where(AchievementApplication.status == status_filter)
    if type_filter is not None:
        query = query.where(AchievementApplication.type == type_filter)
    if student_id is not None:
        query = query.where(AchievementApplication.student_id == student_id)
    result = await db.execute(query.order_by(AchievementApplication.submitted_at.desc()))
    return {"items": [serialize_model(record) for record in result.scalars().all()]}


async def my_achievements(
    current_user: User,
    db: AsyncSession,
) -> dict[str, Any]:
    student = await get_student_profile_or_404(db, current_user.id)
    result = await db.execute(select(AchievementApplication).where(AchievementApplication.student_id == student.id).order_by(AchievementApplication.submitted_at.desc()))
    return {"items": [serialize_model(record) for record in result.scalars().all()]}


async def achievement_detail(
    current_user: User,
    achievement_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    result = await db.execute(select(AchievementApplication).where(AchievementApplication.id == achievement_id))
    achievement = result.scalar_one_or_none()
    if achievement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Achievement not found")
    if current_user.role == "student":
        student = await get_student_profile_or_404(db, current_user.id)
        if student.id != achievement.student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return serialize_model(achievement)


async def approve_achievement(
    achievement_id: int,
    payload: AchievementReviewPayload,
    current_user: User,
    db: AsyncSession,
) -> dict[str, Any]:
    result = await db.execute(select(AchievementApplication).where(AchievementApplication.id == achievement_id))
    achievement = result.scalar_one_or_none()
    if achievement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Achievement not found")
    achievement.status = AchievementStatus.approved
    achievement.points_approved = clamp(payload.points_approved or achievement.points_claimed, 0.0, ACHIEVEMENT_LIMITS[achievement.type])
    achievement.admin_note = payload.admin_note
    achievement.reviewed_by_id = current_user.id
    achievement.reviewed_at = achievement.reviewed_at or achievement.reviewed_at
    db.add(achievement)
    await db.commit()
    semester, academic_year = await resolve_scope(db, achievement.semester_id)
    await recalculate_and_refresh(
        db, achievement.student_id, semester.id, academic_year.id,
        actor_id=current_user.id, reason="achievement approved",
    )
    return {"message": "Achievement approved"}


async def reject_achievement(
    achievement_id: int,
    payload: AchievementReviewPayload,
    current_user: User,
    db: AsyncSession,
) -> dict[str, Any]:
    result = await db.execute(select(AchievementApplication).where(AchievementApplication.id == achievement_id))
    achievement = result.scalar_one_or_none()
    if achievement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Achievement not found")
    achievement.status = AchievementStatus.rejected
    achievement.admin_note = payload.admin_note
    achievement.reviewed_by_id = current_user.id
    achievement.reviewed_at = achievement.reviewed_at or achievement.reviewed_at
    db.add(achievement)
    await db.commit()
    semester, academic_year = await resolve_scope(db, achievement.semester_id)
    await recalculate_and_refresh(
        db, achievement.student_id, semester.id, academic_year.id,
        actor_id=current_user.id, reason="achievement rejected",
    )
    return {"message": "Achievement rejected"}


async def delete_achievement(
    current_user: User,
    achievement_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    result = await db.execute(select(AchievementApplication).where(AchievementApplication.id == achievement_id))
    achievement = result.scalar_one_or_none()
    if achievement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Achievement not found")
    if current_user.role == "student":
        student = await get_student_profile_or_404(db, current_user.id)
        if student.id != achievement.student_id or achievement.status != AchievementStatus.pending:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete this achievement")
    await db.delete(achievement)
    await db.commit()
    return {"message": "Achievement deleted"}
