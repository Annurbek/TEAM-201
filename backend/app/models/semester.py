from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Semester(Base):
    __tablename__ = "semesters"
    __table_args__ = (
        UniqueConstraint("academic_year_id", "number", name="uq_year_semester_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 or 2
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    academic_year: Mapped["AcademicYear"] = relationship(back_populates="semesters")
    rankings: Mapped[List["RankingSnapshot"]] = relationship(back_populates="semester")
