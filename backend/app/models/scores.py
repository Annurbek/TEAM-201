from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ReviewStatus, WorkType


class AcademicScore(Base):
    __tablename__ = "academic_scores"
    __table_args__ = (
        # Note: UniqueConstraint("student_id", "semester_id", name="uq_academic_score_student_semester"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"), nullable=False)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id"), nullable=False)
    average_gpa: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student: Mapped["StudentProfile"] = relationship(back_populates="academic_scores")
    semester: Mapped["Semester"] = relationship()


class AttendanceScore(Base):
    __tablename__ = "attendance_scores"
    __table_args__ = (
        # Note: UniqueConstraint("student_id", "semester_id", name="uq_attendance_score_student_semester"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"), nullable=False)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id"), nullable=False)
    percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student: Mapped["StudentProfile"] = relationship(back_populates="attendance_scores")
    semester: Mapped["Semester"] = relationship()


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"), nullable=False)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[ReviewStatus] = mapped_column(SAEnum(ReviewStatus), default=ReviewStatus.pending, nullable=False)
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    student: Mapped["StudentProfile"] = relationship(back_populates="certificates")
    semester: Mapped["Semester"] = relationship()
    reviewed_by: Mapped[Optional["User"]] = relationship()


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"), nullable=False)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[ReviewStatus] = mapped_column(SAEnum(ReviewStatus), default=ReviewStatus.pending, nullable=False)
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    student: Mapped["StudentProfile"] = relationship(back_populates="projects")
    semester: Mapped["Semester"] = relationship()
    reviewed_by: Mapped[Optional["User"]] = relationship()


class DisciplineScore(Base):
    __tablename__ = "discipline_scores"
    __table_args__ = (
        # Note: UniqueConstraint("student_id", "semester_id", name="uq_discipline_student_semester"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"), nullable=False)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id"), nullable=False)
    points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student: Mapped["StudentProfile"] = relationship(back_populates="discipline_scores")
    semester: Mapped["Semester"] = relationship()
    updated_by: Mapped[Optional["User"]] = relationship()


class TutorScore(Base):
    __tablename__ = "tutor_scores"
    __table_args__ = (
        # Note: UniqueConstraint("student_id", "semester_id", name="uq_tutor_score_student_semester"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"), nullable=False)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("tutor_profiles.id"), nullable=False)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id"), nullable=False)
    points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student: Mapped["StudentProfile"] = relationship(back_populates="tutor_scores")
    tutor: Mapped["TutorProfile"] = relationship(back_populates="tutor_scores")
    semester: Mapped["Semester"] = relationship()


class WorkScore(Base):
    __tablename__ = "work_scores"
    __table_args__ = (
        # Note: UniqueConstraint("student_id", "semester_id", "work_type", name="uq_work_student_semester_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"), nullable=False)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id"), nullable=False)
    work_type: Mapped[WorkType] = mapped_column(SAEnum(WorkType), nullable=False)
    points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    updated_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student: Mapped["StudentProfile"] = relationship(back_populates="work_scores")
    semester: Mapped["Semester"] = relationship()
    updated_by: Mapped[Optional["User"]] = relationship()
