from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.auth_controller import get_current_user_info, login_user
from app.core.security import get_current_user
from app.db.database import get_db
from app.models.users import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    TokenResponse,
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
