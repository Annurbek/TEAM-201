from typing import Callable, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED
from sqlalchemy import select

from app.core.security import decode_access_token
from app.core.config import settings
from app.models.users import User
from app.db.database import async_session_maker

PUBLIC_PATHS: frozenset[str] = frozenset(
    {
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/auth/login",
        "/api/students/leaderboard",
        "/api/students/leaderboard/guest",
    }
)

PUBLIC_PATH_PREFIXES: tuple[str, ...] = ("/docs", "/redoc", "/openapi.json")


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication-only middleware.

    Responsibilities:
    1. Skip public paths (no auth required)
    2. Extract and validate Bearer token
    3. Decode JWT payload
    4. Load user from database
    5. Store user in request.state.user

    NO role checking is performed here.
    Authorization is handled via FastAPI Depends() in route handlers.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if path in PUBLIC_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES):
            return await call_next(request)

        authorization: Optional[str] = request.headers.get("Authorization")
        if not authorization:
            return await call_next(request)

        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return await call_next(request)

        try:
            payload = decode_access_token(token, settings.SECRET_KEY, settings.ALGORITHM)
            user_id = payload.get("sub")
            if user_id is None:
                raise ValueError("Token payload missing subject")
        except Exception:
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content={"success": False, "message": "Unauthorized", "detail": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        async with async_session_maker() as db:
            result = await db.execute(select(User).where(User.id == int(user_id)))
            user = result.scalar_one_or_none()
            if not user:
                return JSONResponse(
                    status_code=HTTP_401_UNAUTHORIZED,
                    content={"success": False, "message": "Unauthorized", "detail": "User not found"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not user.is_active:
                return JSONResponse(
                    status_code=HTTP_401_UNAUTHORIZED,
                    content={"success": False, "message": "Unauthorized", "detail": "Account is disabled"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

            request.state.user = user

        return await call_next(request)
