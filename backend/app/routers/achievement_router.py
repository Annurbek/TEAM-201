"""Achievement router — endpoint definitions for achievement management."""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_role
from app.core.security import get_current_user
from app.db.database import get_db
from app.models import AchievementStatus, AchievementType
from app.models.enums import UserRole
from app.models.users import User
from app.schemas.edumetric import AchievementReviewPayload
from app.controllers.achievement_controller import (
    submit_achievement,
    list_achievements,
    my_achievements,
    achievement_detail,
    approve_achievement,
    reject_achievement,
    delete_achievement,
)
from app.core.config import settings
from pathlib import Path
from uuid import uuid4

router = APIRouter(tags=["Achievements"])


async def _save_upload(upload: UploadFile, subdir: str) -> str:
    destination_dir = Path(settings.UPLOAD_DIR) / subdir
    destination_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "file.bin").suffix or ".bin"
    destination = destination_dir / f"{uuid4().hex}{suffix}"
    with destination.open("wb") as target:
        upload.file.seek(0)
        target.write(upload.file.read())
    return str(destination)


@router.post("/achievements")
async def submit_achievement_endpoint(
    type: AchievementType = Form(...),
    title: str = Form(...),
    description: str | None = Form(None),
    points_claimed: float = Form(...),
    semester_id: int | None = Form(None),
    document: UploadFile | None = File(None),
    current_user: User = Depends(require_role(UserRole.student, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    document_url = await _save_upload(document, "achievements") if document else None
    return await submit_achievement(current_user, type, title, description, points_claimed, semester_id, document_url, db)


@router.get("/achievements")
async def list_achievements_endpoint(
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
    status_filter: AchievementStatus | None = None,
    type_filter: AchievementType | None = None,
    student_id: int | None = None,
):
    return await list_achievements(db, status_filter=status_filter, type_filter=type_filter, student_id=student_id)


@router.get("/achievements/my")
async def my_achievements_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await my_achievements(current_user, db)


@router.get("/achievements/{achievement_id}")
async def achievement_detail_endpoint(
    achievement_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await achievement_detail(current_user, achievement_id, db)


@router.put("/achievements/{achievement_id}/approve")
async def approve_achievement_endpoint(
    achievement_id: int,
    payload: AchievementReviewPayload,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await approve_achievement(achievement_id, payload, current_user, db)


@router.put("/achievements/{achievement_id}/reject")
async def reject_achievement_endpoint(
    achievement_id: int,
    payload: AchievementReviewPayload,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await reject_achievement(achievement_id, payload, current_user, db)


@router.delete("/achievements/{achievement_id}")
async def delete_achievement_endpoint(
    achievement_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await delete_achievement(current_user, achievement_id, db)
