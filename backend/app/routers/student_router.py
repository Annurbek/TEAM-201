"""Student router — endpoint definitions for student management."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_role
from app.core.security import get_current_user
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.users import User
from app.controllers.student_controller import (
    list_students,
    get_student_detail,
    get_student_score,
    get_student_score_history,
    get_student_feed,
    recalculate_student,
)

router = APIRouter(tags=["Students"])


@router.get("/students")
async def list_students_endpoint(
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
    search: str | None = None,
    group_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    return await list_students(db, search=search, group_id=group_id, page=page, size=size)


@router.get("/students/{student_id}")
async def student_detail(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_student_detail(current_user, student_id, db)


@router.get("/students/{student_id}/score")
async def student_score(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_student_score(current_user, student_id, db)


@router.get("/students/{student_id}/score/history")
async def student_score_history(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_student_score_history(current_user, student_id, db)


@router.get("/students/{student_id}/feed")
async def student_feed(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_student_feed(current_user, student_id, db)


@router.post("/students/{student_id}/recalculate")
async def recalculate_student_endpoint(
    student_id: int,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await recalculate_student(current_user, student_id, db)
