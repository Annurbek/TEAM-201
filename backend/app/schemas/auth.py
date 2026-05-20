from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Username is required")
        if " " in normalized:
            raise ValueError("Username must not contain spaces")
        return normalized


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: str = Field(default="bearer")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    full_name: str
    username: str
    phone: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool = Field(default=False)
    message: str
    detail: Optional[str] = None
