from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService


async def login_user(payload: LoginRequest, db: AsyncSession) -> TokenResponse:
    user = await AuthService.authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username, phone, or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    await AuthService.update_last_login(db, user)
    access_token = AuthService.create_access_token_for_user(user)
    return TokenResponse(access_token=access_token)


async def get_current_user_info(current_user: User) -> UserResponse:
    return UserResponse.model_validate(current_user)
