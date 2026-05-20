from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RankingSnapshot(Base):
    __tablename__ = "ranking_snapshots"
    __table_args__ = (
        # Note: UniqueConstraint("student_id", "semester_id", name="uq_ranking_student_semester"),
        # Note: Index("ix_ranking_semester_total", "semester_id", "total_points"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"), nullable=False)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id"), nullable=False)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), nullable=False)

    academic_points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    attendance_points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    certificate_points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    project_points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    discipline_points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tutor_points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    work_points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    penalty_points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rank_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    student: Mapped["StudentProfile"] = relationship(back_populates="ranking_snapshots")
    semester: Mapped["Semester"] = relationship(back_populates="rankings")
    academic_year: Mapped["AcademicYear"] = relationship(back_populates="rankings")
