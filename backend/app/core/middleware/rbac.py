from typing import Callable, List, Optional, Tuple

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
from sqlalchemy import select

from app.core.security import decode_access_token
from app.core.config import settings
from app.models.enums import UserRole
from app.models.users import User
from app.db.database import async_session_maker


API_PREFIX = "/api"
PUBLIC_PATHS: List[str] = [
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    f"{API_PREFIX}/auth/login",
    f"{API_PREFIX}/students/leaderboard",
    f"{API_PREFIX}/students/leaderboard/guest",
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

        def unauthorized(detail: str) -> JSONResponse:
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content={"success": False, "message": "Unauthorized", "detail": detail},
                headers={"WWW-Authenticate": "Bearer"},
            )

        def forbidden(detail: str) -> JSONResponse:
            return JSONResponse(
                status_code=HTTP_403_FORBIDDEN,
                content={"success": False, "message": "Permission denied", "detail": detail},
            )

        authorization: Optional[str] = request.headers.get("Authorization")
        if not authorization:
            return unauthorized("Unauthorized")

        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return unauthorized("Invalid authentication scheme")

        try:
            payload = decode_access_token(token, settings.SECRET_KEY, settings.ALGORITHM)
            user_id = payload.get("sub")
            if user_id is None:
                raise ValueError("Token payload missing subject")
        except Exception as exc:
            return unauthorized("Invalid or expired token")

        async with async_session_maker() as db:
            result = await db.execute(select(User).where(User.id == int(user_id)))
            user = result.scalar_one_or_none()
            if not user:
                return unauthorized("User not found")

            request.state.user = user
            if user.role == UserRole.super_admin:
                return await call_next(request)

            required_roles: List[UserRole] = ALL_ROLES
            for prefix, roles in self.role_requirements_sorted:
                if path.startswith(prefix):
                    required_roles = roles
                    break

            if user.role not in required_roles:
                return forbidden(f"Insufficient permissions. Required one of: {[r.value for r in required_roles]}")

        response: Response = await call_next(request)
        return response
