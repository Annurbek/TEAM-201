"""Admin router — endpoint definitions for admin management."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_role
from app.core.security import get_current_user
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.users import User
from app.schemas.user import UserCreatePayload
from app.schemas.edumetric import NotificationPayload
from app.controllers.admin_controller import (
    admin_dashboard,
    audit_log,
    admin_create_user,
    admin_toggle_user,
    grant_report,
    recalculate_all,
    send_notification,
)

router = APIRouter(tags=["Admin"])


@router.get("/admin/dashboard")
async def admin_dashboard_endpoint(
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await admin_dashboard(db)


@router.get("/admin/audit-log")
async def audit_log_endpoint(
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    return await audit_log(db, page=page, size=size)


@router.post("/admin/users")
async def admin_create_user_endpoint(
    payload: UserCreatePayload,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await admin_create_user(current_user, payload, db)


@router.put("/admin/users/{user_id}/toggle")
async def admin_toggle_user_endpoint(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await admin_toggle_user(user_id, db)


@router.get("/admin/reports/grant")
async def grant_report_endpoint(
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await grant_report(db)


@router.post("/admin/recalculate-all")
async def recalculate_all_endpoint(
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await recalculate_all(current_user, db)


@router.post("/admin/notifications/send")
async def send_notification_endpoint(
    payload: NotificationPayload,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    return await send_notification(payload, db)
