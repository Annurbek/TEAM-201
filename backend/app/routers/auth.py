from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.auth_controller import (
    change_password,
    get_current_user_info,
    login_user,
    update_current_user,
)
from app.core.security import get_current_user
from app.db.database import get_db
from app.models.users import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    TokenResponse,
    UpdateMeRequest,
    UserResponse,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        401: {"model": MessageResponse},
        403: {"model": MessageResponse},
    },
)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    return await login_user(payload, db)


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": MessageResponse},
        403: {"model": MessageResponse},
    },
)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return await get_current_user_info(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
)
async def update_me(
    payload: UpdateMeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    return await update_current_user(db, current_user, payload)


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponse,
)
async def change_password_route(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await change_password(db, current_user, payload)
    return MessageResponse(success=True, message="Password changed")
