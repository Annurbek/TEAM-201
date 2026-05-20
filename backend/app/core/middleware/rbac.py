from typing import Callable, List, Optional, Tuple

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
from sqlalchemy import select

from app.core.security import decode_access_token
from app.core.config import settings
from app.models.enums import UserRole
from app.models.users import User
from app.db.database import async_session_maker


API_PREFIX = "/api/v1"
PUBLIC_PATHS: List[str] = [
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    f"{API_PREFIX}/auth/login",
]
PUBLIC_PATH_PREFIXES: List[str] = ["/docs", "/redoc", "/openapi.json"]
ALL_ROLES: List[UserRole] = [
    UserRole.super_admin,
    UserRole.admin,
    UserRole.tutor,
    UserRole.parent,
    UserRole.student,
]

ROLE_REQUIREMENTS: List[Tuple[str, List[UserRole]]] = [
    (f"{API_PREFIX}/admin", [UserRole.admin]),
    (f"{API_PREFIX}/tutor", [UserRole.tutor, UserRole.admin]),
    (f"{API_PREFIX}/student", [UserRole.student, UserRole.tutor, UserRole.admin]),
]


class RBACMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.role_requirements_sorted = sorted(
            ROLE_REQUIREMENTS, key=lambda x: len(x[0]), reverse=True
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path in PUBLIC_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES):
            return await call_next(request)

        authorization: Optional[str] = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            )

        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            payload = decode_access_token(token, settings.SECRET_KEY, settings.ALGORITHM)
            user_id = payload.get("sub")
            if user_id is None:
                raise ValueError("Token payload missing subject")
        except Exception as exc:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        async with async_session_maker() as db:
            result = await db.execute(select(User).where(User.id == int(user_id)))
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            request.state.user = user
            if user.role == UserRole.super_admin:
                return await call_next(request)

            required_roles: List[UserRole] = ALL_ROLES
            for prefix, roles in self.role_requirements_sorted:
                if path.startswith(prefix):
                    required_roles = roles
                    break

            if user.role not in required_roles:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required one of: {[r.value for r in required_roles]}",
                )

        response: Response = await call_next(request)
        return response
