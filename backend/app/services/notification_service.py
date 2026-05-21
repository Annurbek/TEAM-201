from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, NotificationType


async def create_notification(
    db: AsyncSession,
    *,
    user_id: int,
    title: str,
    message: str,
    notification_type: NotificationType = NotificationType.info,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification