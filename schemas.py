from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    super_admin = "super_admin"
    admin = "admin"
    student = "student"
    parent = "parent"
    tutor = "tutor"


class WorkType(str, Enum):
    freelance = "freelance"
    part_time = "part_time"
    full_time = "full_time"


class ReviewStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class PenaltyStatus(str, Enum):
    active = "active"
    partially_covered = "partially_covered"
    covered = "covered"


class AuditAction(str, Enum):
    create = "create"
    update = "update"
    delete = "delete"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=50)
    role: UserRole


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=50)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StudentBase(BaseModel):
    student_code: Optional[str] = Field(default=None, max_length=50)
    admission_year: Optional[int] = None
    current_group_id: Optional[int] = None


class StudentCreate(StudentBase):
    user_id: int


class StudentUpdate(BaseModel):
    student_code: Optional[str] = Field(default=None, max_length=50)
    admission_year: Optional[int] = None
    current_group_id: Optional[int] = None


class StudentResponse(StudentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user: UserResponse
    created_at: datetime


class ParentBase(BaseModel):
    pass


class ParentCreate(ParentBase):
    user_id: int


class ParentResponse(ParentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user: UserResponse
    created_at: datetime


class TutorBase(BaseModel):
    pass


class TutorCreate(TutorBase):
    user_id: int


class TutorResponse(TutorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user: UserResponse
    created_at: datetime


class GroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    course: int
    academic_year_id: int


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    course: Optional[int] = None
    academic_year_id: Optional[int] = None


class GroupResponse(GroupBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class AcademicYearBase(BaseModel):
    name: str = Field(..., max_length=20)
    start_date: datetime
    end_date: datetime
    is_current: bool = False


class AcademicYearCreate(AcademicYearBase):
    pass


class AcademicYearUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=20)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_current: Optional[bool] = None


class AcademicYearResponse(AcademicYearBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class SemesterBase(BaseModel):
    academic_year_id: int
    number: int = Field(..., ge=1, le=2)
    start_date: datetime
    end_date: datetime
    is_current: bool = False


class SemesterCreate(SemesterBase):
    pass


class SemesterUpdate(BaseModel):
    academic_year_id: Optional[int] = None
    number: Optional[int] = Field(default=None, ge=1, le=2)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_current: Optional[bool] = None


class SemesterResponse(SemesterBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class AcademicScoreUpdate(BaseModel):
    average_gpa: float = Field(..., ge=0, le=5)


class AcademicScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    semester_id: int
    average_gpa: float
    percent: float
    points: float
    updated_at: datetime


class AttendanceScoreUpdate(BaseModel):
    percent: float = Field(..., ge=0, le=100)


class AttendanceScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    semester_id: int
    percent: float
    points: float
    updated_at: datetime


class CertificateCreate(BaseModel):
    student_id: int
    semester_id: int
    title: str = Field(..., max_length=255)
    file_url: str = Field(..., max_length=500)


class CertificateReview(BaseModel):
    points: float = Field(..., ge=0)
    status: ReviewStatus
    reviewed_by_id: Optional[int] = None


class CertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    semester_id: int
    title: str
    file_url: str
    points: float
    status: ReviewStatus
    reviewed_by_id: Optional[int]
    reviewed_at: Optional[datetime]
    created_at: datetime


class ProjectCreate(BaseModel):
    student_id: int
    semester_id: int
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    file_url: Optional[str] = None


class ProjectReview(BaseModel):
    points: float = Field(..., ge=0)
    status: ReviewStatus
    reviewed_by_id: Optional[int] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    semester_id: int
    title: str
    description: Optional[str]
    file_url: Optional[str]
    points: float
    status: ReviewStatus
    reviewed_by_id: Optional[int]
    reviewed_at: Optional[datetime]
    created_at: datetime


class DisciplineScoreUpdate(BaseModel):
    points: float = Field(..., ge=0)
    comment: Optional[str] = None


class DisciplineScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    semester_id: int
    points: float
    comment: Optional[str]
    updated_by_id: Optional[int]
    updated_at: datetime


class TutorScoreUpdate(BaseModel):
    student_id: int
    semester_id: int
    points: float = Field(..., ge=0)
    comment: Optional[str] = None


class TutorScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    tutor_id: int
    semester_id: int
    points: float
    comment: Optional[str]
    updated_at: datetime


class WorkScoreUpdate(BaseModel):
    student_id: int
    semester_id: int
    work_type: WorkType
    points: float = Field(..., ge=0)


class WorkScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    semester_id: int
    work_type: WorkType
    points: float
    updated_by_id: Optional[int]
    updated_at: datetime


class PenaltyCreate(BaseModel):
    student_id: int
    semester_id: int
    amount: int = Field(..., ge=1, le=20)
    comment: Optional[str] = None


class PenaltyCoverageCreate(BaseModel):
    penalty_id: int
    amount: int = Field(..., ge=1)


class PenaltyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    semester_id: int
    amount: int
    covered_amount: int
    comment: Optional[str]
    status: PenaltyStatus
    created_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime


class RankingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: int
    semester_id: int
    academic_year_id: int
    academic_points: float
    attendance_points: float
    certificate_points: float
    project_points: float
    discipline_points: float
    tutor_points: float
    work_points: float
    penalty_points: float
    total_points: float
    rank_position: Optional[int]
    calculated_at: datetime


class ScoreHistoryLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    actor_id: Optional[int]
    field_name: str
    old_value: Optional[str]
    new_value: Optional[str]
    reason: Optional[str]
    created_at: datetime


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: Optional[int]
    action: AuditAction
    model_name: str
    record_id: Optional[int]
    request_path: Optional[str]
    request_method: Optional[str]
    old_data: Optional[str]
    new_data: Optional[str]
    created_at: datetime
