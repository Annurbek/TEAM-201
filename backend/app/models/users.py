from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Boolean,
    Enum as SAEnum,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.models.base import Base
from app.models.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    student_profile: Mapped[Optional["StudentProfile"]] = relationship(
        back_populates="user", uselist=False
    )
    parent_profile: Mapped[Optional["ParentProfile"]] = relationship(
        back_populates="user", uselist=False
    )
    tutor_profile: Mapped[Optional["TutorProfile"]] = relationship(
        back_populates="user", uselist=False
    )

    created_audit_logs: Mapped[List["AuditLog"]] = relationship(
        back_populates="actor", foreign_keys="AuditLog.actor_id"
    )
    created_score_logs: Mapped[List["ScoreHistoryLog"]] = relationship(
        back_populates="actor", foreign_keys="ScoreHistoryLog.actor_id"
    )
