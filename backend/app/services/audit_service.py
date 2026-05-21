from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditAction, AuditLog


async def log_audit(
    db: AsyncSession,
    *,
    actor_id: int | None,
    action: AuditAction,
    model_name: str,
    record_id: int | None,
    request_path: str | None = None,
    request_method: str | None = None,
    old_data: dict[str, Any] | None = None,
    new_data: dict[str, Any] | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_id=actor_id,
        action=action,
        model_name=model_name,
        record_id=record_id,
        request_path=request_path,
        request_method=request_method,
        old_data=None if old_data is None else json.dumps(old_data, ensure_ascii=False),
        new_data=None if new_data is None else json.dumps(new_data, ensure_ascii=False),
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log
