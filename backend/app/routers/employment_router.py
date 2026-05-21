"""Employment router — endpoint definitions for employment management."""

from fastapi import APIRouter, Body, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_role
from app.core.security import get_current_user
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.users import User
from app.schemas.edumetric import EmploymentPayload
from app.controllers.employment_controller import (
    create_employment,
    my_employment,
    list_employment,
    verify_employment,
)
from app.core.config import settings
from pathlib import Path
from uuid import uuid4

router = APIRouter(tags=["Employment"])


async def _save_upload(upload: UploadFile, subdir: str) -> str:
    destination_dir = Path(settings.UPLOAD_DIR) / subdir
    destination_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "file.bin").suffix or ".bin"
    destination = destination_dir / f"{uuid4().hex}{suffix}"
    with destination.open("wb") as target:
        upload.file.seek(0)
        target.write(upload.file.read())
    return str(destination)


@router.post("/employment")
async def create_employment_endpoint(
    payload: EmploymentPayload,
    document: UploadFile | None = File(None),
    current_user: User = Depends(require_role(UserRole.student, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    document_url = await _save_upload(document, "employment") if document else None
    return await create_employment(current_user, payload, document_url, db)


@router.get("/employment/my")
async def my_employment_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await my_employment(current_user, db)


@router.get("/employment")
async def list_employment_endpoint(
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await list_employment(db)


@router.put("/employment/{employment_id}/verify")
async def verify_employment_endpoint(
    employment_id: int,
    bonus_points: float = Body(..., ge=0),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await verify_employment(employment_id, bonus_points, current_user, db)
