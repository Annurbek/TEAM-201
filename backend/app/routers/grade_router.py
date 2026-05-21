"""Grade router — endpoint definitions for grade management."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_role
from app.core.security import get_current_user
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.users import User
from app.schemas.edumetric import GradeCreatePayload, GradeUpdatePayload
from app.controllers.grade_controller import (
    create_grade,
    list_grades,
    update_grade,
    delete_grade,
    grade_stats,
)

router = APIRouter(tags=["Grades"])


@router.post("/grades")
async def create_grade_endpoint(
    payload: GradeCreatePayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await create_grade(current_user, payload, db)


@router.get("/grades/{student_id}")
async def list_grades_endpoint(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_grades(current_user, student_id, db)


@router.put("/grades/{grade_id}")
async def update_grade_endpoint(
    grade_id: int,
    payload: GradeUpdatePayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await update_grade(grade_id, payload, current_user, db)


@router.delete("/grades/{grade_id}")
async def delete_grade_endpoint(
    grade_id: int,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await delete_grade(grade_id, current_user, db)


@router.get("/grades/stats/{student_id}")
async def grade_stats_endpoint(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await grade_stats(current_user, student_id, db)
