from typing import Callable, List, Tuple
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
from sqlalchemy import select

from app.core.security import decode_access_token
from app.core.config import settings
from app.models.enums import UserRole
from app.models.users import User
from app.db.database import async_session_maker


# Define public paths that do not require authentication
PUBLIC_PATHS: List[str] = [
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/auth/login",
    "/auth/register",
    "/auth/refresh-token",
]

# Define role requirements for path prefixes
# Format: (prefix, [list of allowed roles])
# Note: Super admin is allowed everywhere by default
ROLE_REQUIREMENTS: List[Tuple[str, List[UserRole]]] = [
    ("/admin", [UserRole.admin]),
    ("/tutor", [UserRole.tutor, UserRole.admin]),
    ("/student", [UserRole.student, UserRole.tutor, UserRole.admin]),
    # Default: at least student role (if no prefix matches)
]


class RBACMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # Sort ROLE_REQUIREMENTS by prefix length (descending) to match longest prefix first
        self.role_requirements_sorted = sorted(
            ROLE_REQUIREMENTS, key=lambda x: len(x[0]), reverse=True
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip middleware for public paths
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # Extract token from Authorization header
        authorization: str = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            payload = decode_access_token(
                token, settings.SECRET_KEY, settings.ALGORITHM
            )
            user_id: int = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except Exception:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Fetch user from database
        async with async_session_maker() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Super admin is allowed everywhere
            if user.role == UserRole.super_admin:
                return await call_next(request)

            # Check role based on path
            path = request.url.path
            required_roles: List[UserRole] = [UserRole.student]  # Default

            # Find the longest matching prefix
            for prefix, roles in self.role_requirements_sorted:
                if path.startswith(prefix):
                    required_roles = roles
                    break

            if user.role not in required_roles:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required one of: {[r.value for r in required_roles]}",
                )

        # If all checks pass, call the next middleware/endpoint
        response: Response = await call_next(request)
        return response
