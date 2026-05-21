from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.edumetric import (
    AttendanceStatus,
    FeedbackType,
    NotificationType,
    SentimentType,
)
from app.models.enums import WorkType


class AttendanceCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: int
    course_id: int
    semester_id: Optional[int] = None
    date: str
    status: AttendanceStatus
    note: Optional[str] = None


class AttendanceBulkPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    course_id: int
    semester_id: Optional[int] = None
    date: str
    records: list[dict[str, Any]]


class GradeCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: int
    course_id: int
    semester_id: Optional[int] = None
    assignment_name: str
    score: float
    max_score: float = 100.0
    submission_date: Optional[str] = None
    deadline: Optional[str] = None
    is_late: bool = False
    quality: Optional[str] = None
    is_independent: bool = True


class GradeUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignment_name: Optional[str] = None
    score: Optional[float] = None
    max_score: Optional[float] = None
    submission_date: Optional[str] = None
    deadline: Optional[str] = None
    is_late: Optional[bool] = None
    quality: Optional[str] = None
    is_independent: Optional[bool] = None


class AchievementReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    points_approved: Optional[float] = None
    admin_note: Optional[str] = None


class FeedbackCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: int
    course_id: Optional[int] = None
    type: FeedbackType
    content: str
    sentiment: Optional[SentimentType] = None
    is_visible_to_student: bool = True


class FeedbackUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: Optional[str] = None
    sentiment: Optional[SentimentType] = None
    is_visible_to_student: Optional[bool] = None


class TutorRatingPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: int
    semester: Optional[int] = None
    year: Optional[int] = None
    corporate_culture: float = 0.0
    social_activity: float = 0.0
    soft_skills: float = 0.0
    discipline: float = 0.0
    dorm_activity: float = 0.0
    note: Optional[str] = None


class PenaltyCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: int
    type: str
    reason: str
    points: float
    semester_id: Optional[int] = None


class RecoveryTaskPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: int
    task_description: str
    points_recoverable: float
    semester_id: Optional[int] = None
    due_date: Optional[str] = None


class EmploymentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: int
    company_name: str
    position: str
    type: WorkType
    hours_per_week: Optional[int] = None
    start_date: str
    end_date: Optional[str] = None
    is_it_related: bool = True
    bonus_points: float = 0.0
    semester_id: Optional[int] = None
    semester: int
    year: int


class CoursePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    code: str
    mentor_id: Optional[int] = None
    year: int
    semester: int
    max_hours: int = 80


class GroupPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    course: int
    academic_year_id: int


class AcademicYearPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    start_date: datetime
    end_date: datetime
    is_current: bool = False


class SemesterPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    academic_year_id: int
    number: int
    start_date: datetime
    end_date: datetime
    is_current: bool = False


class NotificationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int
    title: str
    message: str
    type: NotificationType = NotificationType.info
