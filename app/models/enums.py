from __future__ import annotations

from enum import Enum

from sqlalchemy import Enum as SAEnum


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


class PenaltyStatus(str, Enum):
    active = "active"
    partially_covered = "partially_covered"
    covered = "covered"


class ReviewStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class AuditAction(str, Enum):
    create = "create"
    update = "update"
    delete = "delete"