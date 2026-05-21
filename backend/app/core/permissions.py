"""Role-based and permission-based authorization dependencies.

Usage in routers:
    from app.core.permissions import require_role, require_permission
    from app.models.permissions import Permission

    @router.get("/admin/dashboard")
    async def dashboard(user: User = Depends(require_role(UserRole.admin, UserRole.super_admin))):
        ...

    @router.get("/scores/history")
    async def history(user: User = Depends(require_permission(Permission.score_history_edit))):
        ...

    # Or with raw string (less safe, but works):
    async def history(user: User = Depends(require_permission("score_history.edit"))):
        ...
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Union

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.permissions import Permission, ROLE_PERMISSIONS, get_role_permissions
from app.models.users import User

ROLE_HIERARCHY: dict[UserRole, int] = {
    UserRole.student: 1,
    UserRole.parent: 2,
    UserRole.tutor: 3,
    UserRole.admin: 4,
    UserRole.super_admin: 5,
}

ADMIN_ROLES: frozenset[UserRole] = frozenset({UserRole.admin, UserRole.super_admin})
TUTOR_ROLES: frozenset[UserRole] = frozenset({UserRole.tutor, UserRole.admin, UserRole.super_admin})
STAFF_ROLES: frozenset[UserRole] = frozenset({UserRole.tutor, UserRole.admin, UserRole.super_admin, UserRole.parent})

PermissionLike = Union[Permission, str]


def _resolve_permission(p: PermissionLike) -> str:
    """Convert Permission enum or string to string value."""
    return p.value if isinstance(p, Permission) else p


def require_role(*allowed_roles: UserRole) -> Callable:
    """Require the current user to have one of the specified roles.

    Example:
        user: User = Depends(require_role(UserRole.admin, UserRole.super_admin))
    """

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            allowed = [r.value for r in allowed_roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {', '.join(allowed)}",
            )
        return current_user

    return dependency


def require_any_role(*allowed_roles: UserRole) -> Callable:
    """Alias for require_role — checks if user has ANY of the given roles."""
    return require_role(*allowed_roles)


def require_all_roles(*required_roles: UserRole) -> Callable:
    """Require the user to have ALL specified roles (rarely needed)."""

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return dependency


def require_min_role(min_role: UserRole) -> Callable:
    """Require the user to have at least the specified role level in the hierarchy.

    Hierarchy: student(1) < parent(2) < tutor(3) < admin(4) < super_admin(5)

    Example:
        user: User = Depends(require_min_role(UserRole.tutor))
        # Allows: tutor, admin, super_admin
    """
    min_level = ROLE_HIERARCHY.get(min_role, 0)

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        user_level = ROLE_HIERARCHY.get(current_user.role, 0)
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Minimum role required: {min_role.value}",
            )
        return current_user

    return dependency


def require_permission(*required_permissions: PermissionLike) -> Callable:
    """Require the current user to have specific permissions.

    Permissions are stored on the User model as a JSON list of strings.
    This is IN ADDITION to role-based checks.

    Accepts Permission enum values or raw strings:
        require_permission(Permission.score_history_edit)
        require_permission("score_history.edit")
        require_permission(Permission.user_create, Permission.user_edit)

    Usage:
        user: User = Depends(require_permission(Permission.score_history_edit))
    """
    required = [_resolve_permission(p) for p in required_permissions]

    async def dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        user_permissions = getattr(current_user, "permissions", None) or []

        for perm in required:
            if perm not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing permission: {perm}",
                )

        return current_user

    return dependency


def require_admin() -> Callable:
    """Shorthand for requiring admin or super_admin role."""
    return require_role(UserRole.admin, UserRole.super_admin)


def require_tutor() -> Callable:
    """Shorthand for requiring tutor, admin, or super_admin role."""
    return require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)


def require_staff() -> Callable:
    """Shorthand for requiring any staff role (tutor+)."""
    return require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin, UserRole.parent)


def require_score_history_edit() -> Callable:
    """Require admin/super_admin role OR score_history.edit permission."""

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role in {UserRole.admin, UserRole.super_admin}:
            return current_user

        user_perms = getattr(current_user, "permissions", None) or []
        if Permission.score_history_edit.value not in user_perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to modify score history",
            )
        return current_user

    return dependency


def require_role_or_permission(*allowed_roles: UserRole, permission: PermissionLike) -> Callable:
    """Require EITHER one of the roles OR the specified permission.

    Example:
        # Admin can edit, OR anyone with the explicit permission
        user: User = Depends(
            require_role_or_permission(
                UserRole.admin, UserRole.super_admin,
                permission=Permission.score_history_edit
            )
        )
    """
    perm_str = _resolve_permission(permission)

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role in allowed_roles:
            return current_user

        user_perms = getattr(current_user, "permissions", None) or []
        if perm_str in user_perms:
            return current_user

        allowed = [r.value for r in allowed_roles]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required role: {', '.join(allowed)} OR permission: {perm_str}",
        )

    return dependency


def optional_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Return current user if authenticated, None otherwise.

    Use this for endpoints that work for both authenticated and anonymous users.

    Usage:
        user: User | None = Depends(optional_current_user)
    """
    user = getattr(request.state, "user", None)
    if user is not None:
        return user

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None

    try:
        from app.core.security import decode_access_token
        from app.core.config import settings
        from sqlalchemy import select
        from app.models.users import User as UserModel

        payload = decode_access_token(token, settings.SECRET_KEY, settings.ALGORITHM)
        user_id = payload.get("sub")
        if user_id is None:
            return None

        import asyncio

        async def _fetch():
            result = await db.execute(select(UserModel).where(UserModel.id == int(user_id)))
            return result.scalar_one_or_none()

        return asyncio.get_event_loop().run_until_complete(_fetch())
    except Exception:
        return None
