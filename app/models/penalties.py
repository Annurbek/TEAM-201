from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import PenaltyStatus


class Penalty(Base):
    __tablename__ = "penalties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"), nullable=False)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    covered_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[PenaltyStatus] = mapped_column(
        SAEnum(PenaltyStatus), default=PenaltyStatus.active, nullable=False
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student: Mapped["StudentProfile"] = relationship(back_populates="penalties")
    semester: Mapped["Semester"] = relationship()
    created_by: Mapped[Optional["User"]] = relationship()
    coverages: Mapped[List["PenaltyCoverage"]] = relationship(back_populates="penalty")


class PenaltyCoverage(Base):
    __tablename__ = "penalty_coverages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    penalty_id: Mapped[int] = mapped_column(ForeignKey("penalties.id"), nullable=False)
    covered_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    penalty: Mapped["Penalty"] = relationship(back_populates="coverages")
    covered_by: Mapped[Optional["User"]] = relationship()
