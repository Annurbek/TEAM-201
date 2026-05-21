from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole


class UserCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(..., min_length=2, max_length=255)
    username: Optional[str] = Field(default=None, max_length=255)
    password: Optional[str] = Field(default=None, min_length=8)
    role: UserRole = Field(default=UserRole.student)
    phone: Optional[str] = Field(default=None, max_length=50)
    student_code: Optional[str] = Field(default=None, max_length=50)
    current_group_id: Optional[int] = None
    admission_year: Optional[int] = None


class UserUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    is_active: Optional[bool] = None
