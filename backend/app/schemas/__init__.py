from app.schemas.auth import *
from app.schemas.user import *
from app.schemas.edumetric import *

from app.schemas.auth import (
    LoginRequest,
    ChangePasswordRequest,
    UpdateMeRequest,
    TokenResponse,
    UserResponse,
    MessageResponse,
)

from app.schemas.user import (
    UserCreatePayload,
    UserUpdatePayload,
)

from app.schemas.edumetric import (
    AttendanceCreatePayload,
    AttendanceBulkPayload,
    GradeCreatePayload,
    GradeUpdatePayload,
    AchievementReviewPayload,
    FeedbackCreatePayload,
    FeedbackUpdatePayload,
    TutorRatingPayload,
    PenaltyCreatePayload,
    RecoveryTaskPayload,
    EmploymentPayload,
    CoursePayload,
    GroupPayload,
    AcademicYearPayload,
    SemesterPayload,
    NotificationPayload,
)

__all__ = [
    # Auth
    "LoginRequest",
    "ChangePasswordRequest",
    "UpdateMeRequest",
    "TokenResponse",
    "UserResponse",
    "MessageResponse",
    # User
    "UserCreatePayload",
    "UserUpdatePayload",
    # Edumetric
    "AttendanceCreatePayload",
    "AttendanceBulkPayload",
    "GradeCreatePayload",
    "GradeUpdatePayload",
    "AchievementReviewPayload",
    "FeedbackCreatePayload",
    "FeedbackUpdatePayload",
    "TutorRatingPayload",
    "PenaltyCreatePayload",
    "RecoveryTaskPayload",
    "EmploymentPayload",
    "CoursePayload",
    "GroupPayload",
    "AcademicYearPayload",
    "SemesterPayload",
    "NotificationPayload",
]
