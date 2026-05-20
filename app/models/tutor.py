from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TutorProfile(Base):
    __tablename__ = "tutor_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="tutor_profile")
    groups: Mapped[List["TutorGroupLink"]] = relationship(back_populates="tutor")
    tutor_scores: Mapped[List["TutorScore"]] = relationship(back_populates="tutor")


class StudentParentLink(Base):
    __tablename__ = "student_parent_links"
    __table_args__ = (
        # Note: The original had UniqueConstraint("student_id", name="uq_one_parent_per_student"),
        # but we'll keep it as is for now.
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"), nullable=False)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parent_profiles.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    student: Mapped["StudentProfile"] = relationship(back_populates="parent_links")
    parent: Mapped["ParentProfile"] = relationship(back_populates="children")


class StudentGroupMembership(Base):
    __tablename__ = "student_group_memberships"
    __table_args__ = (
        # Note: The original had UniqueConstraint("student_id", "group_id", "academic_year_id", name="uq_student_group_year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"), nullable=False)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    left_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    student: Mapped["StudentProfile"] = relationship(back_populates="group_memberships")
    group: Mapped["Group"] = relationship(back_populates="students")


class TutorGroupLink(Base):
    __tablename__ = "tutor_group_links"
    __table_args__ = (
        # Note: The original had UniqueConstraint("tutor_id", "group_id", "academic_year_id", name="uq_tutor_group_year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("tutor_profiles.id"), nullable=False)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    tutor: Mapped["TutorProfile"] = relationship(back_populates="groups")
    group: Mapped["Group"] = relationship(back_populates="tutor_links")
