"""Penalty controller — business logic for penalty and recovery endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Penalty, RecoveryTask, Semester, User
from app.schemas.edumetric import PenaltyCreatePayload, RecoveryTaskPayload
from app.services.edumetric_service import (
    check_student_access,
    get_student_profile_or_404,
    recalculate_and_refresh,
    resolve_scope,
    serialize_model,
)
from app.services.score_service import get_current_semester, get_current_academic_year
from app.models.enums import PenaltyStatus
from app.services.score_service import clamp


async def create_penalty(
    current_user: User,
    payload: PenaltyCreatePayload,
    db: AsyncSession,
) -> dict[str, Any]:
    semester, academic_year = await resolve_scope(db, payload.semester_id)
    penalty = Penalty(
        student_id=payload.student_id,
        semester_id=semester.id,
        amount=-abs(int(payload.points)),
        covered_amount=0,
        comment=f"{payload.type}: {payload.reason}",
        status=PenaltyStatus.active,
        created_by_id=current_user.id,
    )
    db.add(penalty)
    await db.commit()
    await recalculate_and_refresh(
        db, payload.student_id, semester.id, academic_year.id,
        actor_id=current_user.id, reason=payload.reason,
    )
    return {"id": penalty.id, "message": "Penalty created"}


async def list_penalties(
    current_user: User,
    student_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    await check_student_access(current_user, student_id, db)
    result = await db.execute(select(Penalty).where(Penalty.student_id == student_id).order_by(Penalty.created_at.desc()))
    return {"items": [serialize_model(record) for record in result.scalars().all()]}


async def create_recovery_task(
    current_user: User,
    payload: RecoveryTaskPayload,
    db: AsyncSession,
) -> dict[str, Any]:
    semester, academic_year = await resolve_scope(db, payload.semester_id)
    task = RecoveryTask(
        student_id=payload.student_id,
        assigned_by_id=current_user.id,
        semester_id=semester.id,
        task_description=payload.task_description,
        points_recoverable=clamp(payload.points_recoverable, 0.0, 10.0),
        status="pending",
        due_date=payload.due_date,
    )
    db.add(task)
    await db.commit()
    return {"id": task.id, "message": "Recovery task created"}


async def complete_recovery_task(
    current_user: User,
    task_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    result = await db.execute(select(RecoveryTask).where(RecoveryTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery task not found")
    student = await get_student_profile_or_404(db, task.student_id)
    if current_user.role == "student" and student.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    db.add(task)
    await db.commit()
    return {"message": "Recovery task marked complete"}


async def verify_recovery_task(
    task_id: int,
    points_recovered: float,
    current_user: User,
    db: AsyncSession,
) -> dict[str, Any]:
    result = await db.execute(select(RecoveryTask).where(RecoveryTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery task not found")
    task.status = "verified"
    task.points_recovered = clamp(points_recovered, 0.0, task.points_recoverable)
    task.verified_at = datetime.utcnow()
    db.add(task)
    await db.commit()
    semester, academic_year = await resolve_scope(db, task.semester_id)
    await recalculate_and_refresh(
        db, task.student_id, semester.id, academic_year.id,
        actor_id=current_user.id, reason="recovery verified",
    )
    return {"message": "Recovery task verified"}
