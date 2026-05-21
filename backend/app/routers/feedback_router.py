"""Feedback router — endpoint definitions for feedback management."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_role
from app.core.security import get_current_user
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.users import User
from app.schemas.edumetric import FeedbackCreatePayload, FeedbackUpdatePayload
from app.controllers.feedback_controller import (
    create_feedback,
    student_feedback,
    my_given_feedback,
    update_feedback,
    delete_feedback,
)

router = APIRouter(tags=["Feedback"])


@router.post("/feedback")
async def create_feedback_endpoint(
    payload: FeedbackCreatePayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await create_feedback(current_user, payload, db)


@router.get("/feedback/student/{student_id}")
async def student_feedback_endpoint(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await student_feedback(current_user, student_id, db)


@router.get("/feedback/my-given")
async def my_given_feedback_endpoint(
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await my_given_feedback(current_user, db)


@router.put("/feedback/{feedback_id}")
async def update_feedback_endpoint(
    feedback_id: int,
    payload: FeedbackUpdatePayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await update_feedback(feedback_id, payload, current_user, db)


@router.delete("/feedback/{feedback_id}")
async def delete_feedback_endpoint(
    feedback_id: int,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await delete_feedback(feedback_id, current_user, db)
