"""Feedback controller — business logic for feedback endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FeedbackEntry, Semester, User
from app.schemas.edumetric import FeedbackCreatePayload, FeedbackUpdatePayload
from app.services.edumetric_service import (
    check_student_access,
    serialize_model,
)
from app.services.score_service import get_current_semester


async def create_feedback(
    current_user: User,
    payload: FeedbackCreatePayload,
    db: AsyncSession,
) -> dict[str, Any]:
    current_semester = await get_current_semester(db)
    feedback = FeedbackEntry(
        mentor_id=current_user.id,
        student_id=payload.student_id,
        course_id=payload.course_id,
        semester_id=current_semester.id if current_semester else None,
        type=payload.type,
        content=payload.content,
        sentiment=payload.sentiment,
        is_visible_to_student=payload.is_visible_to_student,
    )
    db.add(feedback)
    await db.commit()
    return {"id": feedback.id, "message": "Feedback created"}


async def student_feedback(
    current_user: User,
    student_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    await check_student_access(current_user, student_id, db)
    result = await db.execute(select(FeedbackEntry).where(FeedbackEntry.student_id == student_id).order_by(FeedbackEntry.created_at.desc()))
    return {"items": [serialize_model(record) for record in result.scalars().all()]}


async def my_given_feedback(
    current_user: User,
    db: AsyncSession,
) -> dict[str, Any]:
    result = await db.execute(select(FeedbackEntry).where(FeedbackEntry.mentor_id == current_user.id).order_by(FeedbackEntry.created_at.desc()))
    return {"items": [serialize_model(record) for record in result.scalars().all()]}


async def update_feedback(
    feedback_id: int,
    payload: FeedbackUpdatePayload,
    current_user: User,
    db: AsyncSession,
) -> dict[str, Any]:
    result = await db.execute(select(FeedbackEntry).where(FeedbackEntry.id == feedback_id))
    feedback = result.scalar_one_or_none()
    if feedback is None or feedback.mentor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(feedback, field, value)
    db.add(feedback)
    await db.commit()
    return {"message": "Feedback updated"}


async def delete_feedback(
    feedback_id: int,
    current_user: User,
    db: AsyncSession,
) -> dict[str, Any]:
    result = await db.execute(select(FeedbackEntry).where(FeedbackEntry.id == feedback_id))
    feedback = result.scalar_one_or_none()
    if feedback is None or feedback.mentor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    await db.delete(feedback)
    await db.commit()
    return {"message": "Feedback deleted"}
