from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    student_code: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    current_group_id: Mapped[Optional[int]] = mapped_column(ForeignKey("groups.id"), nullable=True)
    admission_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="student_profile")
    current_group: Mapped[Optional["Group"]] = relationship()
    group_memberships: Mapped[List["StudentGroupMembership"]] = relationship(back_populates="student")
    parent_links: Mapped[List["StudentParentLink"]] = relationship(back_populates="student")

    academic_scores: Mapped[List["AcademicScore"]] = relationship(back_populates="student")
    attendance_scores: Mapped[List["AttendanceScore"]] = relationship(back_populates="student")
    certificates: Mapped[List["Certificate"]] = relationship(back_populates="student")
    projects: Mapped[List["Project"]] = relationship(back_populates="student")
    discipline_scores: Mapped[List["DisciplineScore"]] = relationship(back_populates="student")
    tutor_scores: Mapped[List["TutorScore"]] = relationship(back_populates="student")
    work_scores: Mapped[List["WorkScore"]] = relationship(back_populates="student")
    penalties: Mapped[List["Penalty"]] = relationship(back_populates="student")
    ranking_snapshots: Mapped[List["RankingSnapshot"]] = relationship(back_populates="student")
    score_logs: Mapped[List["ScoreHistoryLog"]] = relationship(back_populates="student")
