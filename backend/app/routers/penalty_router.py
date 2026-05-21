"""Penalty router — endpoint definitions for penalty and recovery management."""

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_role
from app.core.security import get_current_user
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.users import User
from app.schemas.edumetric import PenaltyCreatePayload, RecoveryTaskPayload
from app.controllers.penalty_controller import (
    create_penalty,
    list_penalties,
    create_recovery_task,
    complete_recovery_task,
    verify_recovery_task,
)

router = APIRouter(tags=["Penalties & Recovery"])


@router.post("/penalties")
async def create_penalty_endpoint(
    payload: PenaltyCreatePayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await create_penalty(current_user, payload, db)


@router.get("/penalties/{student_id}")
async def list_penalties_endpoint(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_penalties(current_user, student_id, db)


@router.post("/penalties/recovery")
async def create_recovery_task_endpoint(
    payload: RecoveryTaskPayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await create_recovery_task(current_user, payload, db)


@router.put("/penalties/recovery/{task_id}/complete")
async def complete_recovery_task_endpoint(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await complete_recovery_task(current_user, task_id, db)


@router.put("/penalties/recovery/{task_id}/verify")
async def verify_recovery_task_endpoint(
    task_id: int,
    points_recovered: float = Body(..., ge=0),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await verify_recovery_task(task_id, points_recovered, current_user, db)
