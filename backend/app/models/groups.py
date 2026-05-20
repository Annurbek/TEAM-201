from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Group(Base):
    __tablename__ = "groups"
    __table_args__ = (UniqueConstraint("name", "academic_year_id", name="uq_group_year_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    course: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    academic_year: Mapped["AcademicYear"] = relationship()
    students: Mapped[List["StudentGroupMembership"]] = relationship(back_populates="group")
    tutor_links: Mapped[List["TutorGroupLink"]] = relationship(back_populates="group")
