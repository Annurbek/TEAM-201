from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.permissions import require_role, require_any_role, require_min_role, require_score_history_edit
from app.core.security import get_current_user
from app.db.database import get_db
from app.models import (
    AcademicYear,
    AchievementApplication,
    AchievementStatus,
    AchievementType,
    AttendanceRecord,
    AttendanceScore,
    AttendanceStatus,
    AuditAction,
    AuditLog,
    Course,
    EmploymentRecord,
    FeedbackEntry,
    FeedbackType,
    GradeRecord,
    Group,
    NotificationType,
    Penalty,
    RecoveryTask,
    RankingSnapshot,
    ScoreHistoryLog,
    Semester,
    SentimentType,
    StudentProfile,
    TutorRating,
    User,
    UserRole,
    ParentProfile,
    StudentParentLink,
    WorkType,
)
from app.models.enums import PenaltyStatus
from app.schemas.edumetric import (
    AcademicYearPayload,
    AchievementReviewPayload,
    AttendanceBulkPayload,
    AttendanceCreatePayload,
    CoursePayload,
    EmploymentPayload,
    FeedbackCreatePayload,
    FeedbackUpdatePayload,
    GradeCreatePayload,
    GradeUpdatePayload,
    GroupPayload,
    NotificationPayload,
    PenaltyCreatePayload,
    RecoveryTaskPayload,
    SemesterPayload,
    TutorRatingPayload,
)
from app.schemas.user import UserCreatePayload, UserUpdatePayload
from app.services.audit_service import log_audit
from app.services.notification_service import create_notification
from app.services.score_service import (
    calculate_student_score,
    clamp,
    get_current_academic_year,
    get_current_semester,
    get_year_leaderboard,
    recalculate_rankings,
)


router = APIRouter(tags=["Edumetric"])

QUALITY_VALUES = {"excellent", "good", "satisfactory", "poor", "plagiarized"}
ACHIEVEMENT_LIMITS = {
    AchievementType.hackathon_participant: 1,
    AchievementType.hackathon_winner: 3,
    AchievementType.startup: 7,
    AchievementType.mentoring: 3,
    AchievementType.certificate_online: 2,
    AchievementType.certificate_offline: 3,
    AchievementType.certificate_national_it: 2,
    AchievementType.certificate_language: 5,
    AchievementType.certificate_international: 10,
    AchievementType.volunteering: 2,
    AchievementType.soft_skills: 1,
    AchievementType.networking: 1,
    AchievementType.project_participant: 2,
    AchievementType.direction_assistant: 3,
    AchievementType.strategic_assistant: 4,
}


async def _resolve_scope(db: AsyncSession, semester_id: int | None = None, academic_year_id: int | None = None) -> tuple[Semester, AcademicYear]:
    semester = None
    academic_year = None
    if semester_id is None:
        semester = await get_current_semester(db)
    else:
        semester = (await db.execute(select(Semester).where(Semester.id == semester_id))).scalar_one_or_none()
    if semester is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semester not found")

    if academic_year_id is None:
        academic_year = (await db.execute(select(AcademicYear).where(AcademicYear.id == semester.academic_year_id))).scalar_one_or_none()
    else:
        academic_year = (await db.execute(select(AcademicYear).where(AcademicYear.id == academic_year_id))).scalar_one_or_none()
    if academic_year is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")
    return semester, academic_year


async def _save_upload(upload: UploadFile, subdir: str) -> str:
    destination_dir = Path(settings.UPLOAD_DIR) / subdir
    destination_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "file.bin").suffix or ".bin"
    destination = destination_dir / f"{uuid4().hex}{suffix}"
    with destination.open("wb") as target:
        shutil.copyfileobj(upload.file, target)
    return str(destination)


async def _student_profile_or_404(db: AsyncSession, student_id: int) -> StudentProfile:
    result = await db.execute(
        select(StudentProfile).where(or_(StudentProfile.id == student_id, StudentProfile.user_id == student_id))
    )
    student = result.scalar_one_or_none()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


async def _student_access_or_404(current_user: User, student_id: int, db: AsyncSession) -> StudentProfile:
    student = await _student_profile_or_404(db, student_id)
    # Admins, super admins, tutors and mentors have access
    if current_user.role in {UserRole.admin, UserRole.super_admin, UserRole.tutor, UserRole.mentor}:
        return student
    # Student can access their own profile
    if current_user.role == UserRole.student and student.user_id == current_user.id:
        return student
    # Parent can access if linked to the student
    if current_user.role == UserRole.parent:
        result = await db.execute(select(ParentProfile).where(ParentProfile.user_id == current_user.id))
        parent = result.scalar_one_or_none()
        if parent is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        link_result = await db.execute(
            select(StudentParentLink).where(StudentParentLink.student_id == student.id, StudentParentLink.parent_id == parent.id, StudentParentLink.is_active.is_(True))
        )
        link = link_result.scalar_one_or_none()
        if link is not None:
            return student
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


async def _recalculate_and_refresh(
    db: AsyncSession,
    student_id: int,
    semester_id: int,
    academic_year_id: int,
    actor_id: int | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    score = await calculate_student_score(
        db,
        student_id=student_id,
        semester_id=semester_id,
        academic_year_id=academic_year_id,
        actor_id=actor_id,
        reason=reason,
    )
    await recalculate_rankings(db, semester_id=semester_id, academic_year_id=academic_year_id)
    return score


def _serialize_user(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "full_name": user.full_name,
        "username": user.username,
        "phone": user.phone,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "last_login": user.last_login,
    }


def _serialize_model(instance: Any) -> dict[str, Any]:
    return {key: value for key, value in instance.__dict__.items() if not key.startswith("_sa_")}


@router.get("/students/leaderboard/guest")
async def guest_leaderboard(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    academic_year = await get_current_academic_year(db)
    if academic_year is None:
        return {"items": [], "page": page, "size": size, "total": 0}
    leaderboard = await get_year_leaderboard(db, academic_year.id)
    total = len(leaderboard)
    start = (page - 1) * size
    end = start + size
    items = leaderboard[start:end]
    return {"items": items, "page": page, "size": size, "total": total, "academic_year_id": academic_year.id}


@router.get("/students/leaderboard")
async def public_leaderboard(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    academic_year_id: int | None = None,
):
    if academic_year_id is None:
        academic_year = await get_current_academic_year(db)
        if academic_year is None:
            return {"items": [], "page": page, "size": size, "total": 0}
        academic_year_id = academic_year.id
    leaderboard = await get_year_leaderboard(db, academic_year_id)
    total = len(leaderboard)
    start = (page - 1) * size
    end = start + size
    return {"items": leaderboard[start:end], "page": page, "size": size, "total": total, "academic_year_id": academic_year_id}


@router.get("/students")
async def list_students(
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
    search: str | None = None,
    group_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    query = select(StudentProfile, User).join(User, User.id == StudentProfile.user_id)
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(or_(func.lower(User.full_name).like(pattern), func.lower(User.username).like(pattern), func.lower(StudentProfile.student_code).like(pattern)))
    if group_id is not None:
        query = query.where(StudentProfile.current_group_id == group_id)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    result = await db.execute(query.order_by(User.full_name).offset((page - 1) * size).limit(size))
    items = []
    for student, user in result.all():
        items.append({"student_id": student.id, **_serialize_user(user), "student_code": student.student_code, "current_group_id": student.current_group_id, "admission_year": student.admission_year})
    return {"items": items, "page": page, "size": size, "total": total}


@router.get("/students/{student_id}")
async def student_detail(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    student = await _student_access_or_404(current_user, student_id, db)
    user = (await db.execute(select(StudentProfile).where(StudentProfile.id == student_id))).scalar_one()
    semester = await get_current_semester(db)
    academic_year = await get_current_academic_year(db)
    score = None
    if semester and academic_year:
        score = await calculate_student_score(db, student.id, semester.id, academic_year.id)
    return {"student": {"student_id": student.id, **_serialize_user(user), "student_code": student.student_code, "current_group_id": student.current_group_id, "admission_year": student.admission_year}, "score": score}


@router.get("/students/{student_id}/score")
async def student_score(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _student_access_or_404(current_user, student_id, db)
    semester = await get_current_semester(db)
    academic_year = await get_current_academic_year(db)
    if semester is None or academic_year is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current scope not available")
    return await calculate_student_score(db, student_id, semester.id, academic_year.id)


@router.get("/students/{student_id}/score/history")
async def student_score_history(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _student_access_or_404(current_user, student_id, db)
    result = await db.execute(
        select(RankingSnapshot, Semester, AcademicYear)
        .join(Semester, Semester.id == RankingSnapshot.semester_id)
        .join(AcademicYear, AcademicYear.id == RankingSnapshot.academic_year_id)
        .where(RankingSnapshot.student_id == student_id)
        .order_by(AcademicYear.start_date.desc(), Semester.number.desc())
    )
    items = []
    for snapshot, semester, academic_year in result.all():
        items.append({
            "snapshot_id": snapshot.id,
            "semester_id": snapshot.semester_id,
            "academic_year_id": snapshot.academic_year_id,
            "academic_year": academic_year.name,
            "semester": semester.number,
            "academic_points": snapshot.academic_points,
            "attendance_points": snapshot.attendance_points,
            "certificate_points": snapshot.certificate_points,
            "project_points": snapshot.project_points,
            "discipline_points": snapshot.discipline_points,
            "tutor_points": snapshot.tutor_points,
            "work_points": snapshot.work_points,
            "penalty_points": snapshot.penalty_points,
            "total_points": snapshot.total_points,
            "rank_position": snapshot.rank_position,
            "calculated_at": snapshot.calculated_at,
        })
    return {"items": items}


@router.get("/students/{student_id}/feed")
async def student_feed(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _student_access_or_404(current_user, student_id, db)
    items: list[dict[str, Any]] = []

    for table, label in [
        (AttendanceRecord, "attendance"),
        (GradeRecord, "grade"),
        (AchievementApplication, "achievement"),
        (FeedbackEntry, "feedback"),
        (Penalty, "penalty"),
        (RecoveryTask, "recovery"),
        (EmploymentRecord, "employment"),
    ]:
        if table is AttendanceRecord:
            result = await db.execute(select(table).where(table.student_id == student_id).order_by(table.created_at.desc()))
        elif table is GradeRecord:
            result = await db.execute(select(table).where(table.student_id == student_id).order_by(table.created_at.desc()))
        elif table is AchievementApplication:
            result = await db.execute(select(table).where(table.student_id == student_id).order_by(table.submitted_at.desc()))
        elif table is FeedbackEntry:
            result = await db.execute(select(table).where(table.student_id == student_id).order_by(table.created_at.desc()))
        elif table is Penalty:
            result = await db.execute(select(table).where(table.student_id == student_id).order_by(table.created_at.desc()))
        elif table is RecoveryTask:
            result = await db.execute(select(table).where(table.student_id == student_id).order_by(table.created_at.desc()))
        else:
            result = await db.execute(select(table).where(table.student_id == student_id).order_by(table.created_at.desc()))
        for record in result.scalars().all():
            items.append({"type": label, "created_at": getattr(record, "created_at", None) or getattr(record, "submitted_at", None), "data": record})

    result = await db.execute(
        select(ScoreHistoryLog).where(ScoreHistoryLog.student_id == student_id).order_by(ScoreHistoryLog.created_at.desc())
    )
    for record in result.scalars().all():
        items.append({"type": "score_history", "created_at": record.created_at, "data": record})

    items.sort(key=lambda item: item["created_at"] or datetime.min, reverse=True)
    return {"items": items}


@router.post("/students/{student_id}/recalculate")
async def recalculate_student(
    student_id: int,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    semester = await get_current_semester(db)
    academic_year = await get_current_academic_year(db)
    if semester is None or academic_year is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current scope not available")
    score = await _recalculate_and_refresh(db, student_id, semester.id, academic_year.id, actor_id=current_user.id, reason="manual recalculation")
    await log_audit(db, actor_id=current_user.id, action=AuditAction.update, model_name="RankingSnapshot", record_id=score["snapshot_id"], request_path="/students/{student_id}/recalculate", request_method="POST", new_data=score)
    return score


@router.get("/attendance/{student_id}")
async def list_attendance(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    course_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    await _student_access_or_404(current_user, student_id, db)
    query = select(AttendanceRecord).where(AttendanceRecord.student_id == student_id)
    if course_id is not None:
        query = query.where(AttendanceRecord.course_id == course_id)
    if date_from is not None:
        query = query.where(AttendanceRecord.date >= date_from)
    if date_to is not None:
        query = query.where(AttendanceRecord.date <= date_to)
    result = await db.execute(query.order_by(AttendanceRecord.date.desc()))
    return {"items": [_serialize_model(record) for record in result.scalars().all()]}


@router.get("/attendance/course/{course_id}")
async def course_attendance(
    course_id: int,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AttendanceRecord).where(AttendanceRecord.course_id == course_id).order_by(AttendanceRecord.date.desc()))
    return {"items": [_serialize_model(record) for record in result.scalars().all()]}


@router.get("/attendance/stats/{student_id}")
async def attendance_stats(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _student_access_or_404(current_user, student_id, db)
    semester = await get_current_semester(db)
    if semester is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semester not found")
    result = await db.execute(select(AttendanceScore).where(AttendanceScore.student_id == student_id, AttendanceScore.semester_id == semester.id))
    score = result.scalar_one_or_none()
    return {"percent": 0.0 if score is None else score.percent, "points": 0.0 if score is None else score.points}


@router.post("/attendance")
async def create_attendance(
    payload: AttendanceCreatePayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    semester, academic_year = await _resolve_scope(db, payload.semester_id)
    attendance = AttendanceRecord(
        student_id=payload.student_id,
        course_id=payload.course_id,
        semester_id=semester.id,
        date=payload.date,
        status=payload.status,
        recorded_by_id=current_user.id,
        note=payload.note,
    )
    db.add(attendance)
    await db.commit()
    await _recalculate_and_refresh(db, payload.student_id, semester.id, academic_year.id, actor_id=current_user.id, reason="attendance marked")
    await log_audit(db, actor_id=current_user.id, action=AuditAction.create, model_name="AttendanceRecord", record_id=attendance.id, request_path="/attendance", request_method="POST", new_data=payload.model_dump())
    await create_notification(db, user_id=(await _student_profile_or_404(db, payload.student_id)).user_id, title="Attendance updated", message=f"Attendance recorded for {payload.date}", notification_type=NotificationType.info)
    return {"id": attendance.id, "message": "Attendance recorded"}


@router.post("/attendance/bulk")
async def bulk_attendance(
    payload: AttendanceBulkPayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    semester, academic_year = await _resolve_scope(db, payload.semester_id)
    created: list[int] = []
    for record in payload.records:
        attendance = AttendanceRecord(
            student_id=int(record["student_id"]),
            course_id=payload.course_id,
            semester_id=semester.id,
            date=payload.date,
            status=AttendanceStatus(record["status"]),
            recorded_by_id=current_user.id,
        )
        db.add(attendance)
        await db.flush()
        created.append(attendance.id)
        await _recalculate_and_refresh(db, attendance.student_id, semester.id, academic_year.id, actor_id=current_user.id, reason="bulk attendance")
    await db.commit()
    return {"created": created}


@router.put("/attendance/{attendance_id}")
async def update_attendance(
    attendance_id: int,
    payload: AttendanceCreatePayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AttendanceRecord).where(AttendanceRecord.id == attendance_id))
    attendance = result.scalar_one_or_none()
    if attendance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance not found")
    old = _serialize_model(attendance)
    attendance.student_id = payload.student_id
    attendance.course_id = payload.course_id
    attendance.date = payload.date
    attendance.status = payload.status
    attendance.note = payload.note
    db.add(attendance)
    await db.commit()
    semester, academic_year = await _resolve_scope(db, attendance.semester_id)
    await _recalculate_and_refresh(db, attendance.student_id, semester.id, academic_year.id, actor_id=current_user.id, reason="attendance updated")
    await log_audit(db, actor_id=current_user.id, action=AuditAction.update, model_name="AttendanceRecord", record_id=attendance.id, request_path=f"/attendance/{attendance_id}", request_method="PUT", old_data=old, new_data=payload.model_dump())
    return {"message": "Attendance updated"}


@router.post("/grades")
async def create_grade(
    payload: GradeCreatePayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    semester, academic_year = await _resolve_scope(db, payload.semester_id)
    grade = GradeRecord(
        student_id=payload.student_id,
        course_id=payload.course_id,
        semester_id=semester.id,
        assignment_name=payload.assignment_name,
        score=payload.score,
        max_score=payload.max_score,
        submission_date=payload.submission_date,
        deadline=payload.deadline,
        is_late=payload.is_late,
        quality=payload.quality,
        is_independent=payload.is_independent,
        graded_by_id=current_user.id,
    )
    db.add(grade)
    await db.commit()
    await _recalculate_and_refresh(db, payload.student_id, semester.id, academic_year.id, actor_id=current_user.id, reason="grade added")
    await log_audit(db, actor_id=current_user.id, action=AuditAction.create, model_name="GradeRecord", record_id=grade.id, request_path="/grades", request_method="POST", new_data=payload.model_dump())
    return {"id": grade.id, "message": "Grade recorded"}


@router.get("/grades/{student_id}")
async def list_grades(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _student_access_or_404(current_user, student_id, db)
    result = await db.execute(select(GradeRecord).where(GradeRecord.student_id == student_id).order_by(GradeRecord.created_at.desc()))
    return {"items": [_serialize_model(record) for record in result.scalars().all()]}


@router.put("/grades/{grade_id}")
async def update_grade(
    grade_id: int,
    payload: GradeUpdatePayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(GradeRecord).where(GradeRecord.id == grade_id))
    grade = result.scalar_one_or_none()
    if grade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade not found")
    old_student_id = grade.student_id
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(grade, field, value)
    db.add(grade)
    await db.commit()
    semester, academic_year = await _resolve_scope(db, grade.semester_id)
    await _recalculate_and_refresh(db, old_student_id, semester.id, academic_year.id, actor_id=current_user.id, reason="grade updated")
    return {"message": "Grade updated"}


@router.delete("/grades/{grade_id}")
async def delete_grade(
    grade_id: int,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(GradeRecord).where(GradeRecord.id == grade_id))
    grade = result.scalar_one_or_none()
    if grade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade not found")
    student_id = grade.student_id
    semester, academic_year = await _resolve_scope(db, grade.semester_id)
    await db.delete(grade)
    await db.commit()
    await _recalculate_and_refresh(db, student_id, semester.id, academic_year.id, actor_id=current_user.id, reason="grade deleted")
    return {"message": "Grade deleted"}


@router.get("/grades/stats/{student_id}")
async def grade_stats(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _student_access_or_404(current_user, student_id, db)
    result = await db.execute(
        select(func.coalesce(func.avg((GradeRecord.score / func.nullif(GradeRecord.max_score, 0)) * 100), 0.0)).where(GradeRecord.student_id == student_id)
    )
    return {"average_percentage": float(result.scalar_one() or 0.0)}


@router.post("/achievements")
async def submit_achievement(
    type: AchievementType = Form(...),
    title: str = Form(...),
    description: str | None = Form(None),
    points_claimed: float = Form(...),
    semester_id: int | None = Form(None),
    document: UploadFile | None = File(None),
    current_user: User = Depends(require_role(UserRole.student, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    semester, academic_year = await _resolve_scope(db, semester_id)
    student = await _student_profile_or_404(db, current_user.id if current_user.role == UserRole.student else current_user.id)
    document_url = await _save_upload(document, "achievements") if document else None
    achievement = AchievementApplication(
        student_id=student.id,
        semester_id=semester.id,
        type=type,
        title=title,
        description=description,
        document_url=document_url,
        points_claimed=points_claimed,
        status=AchievementStatus.pending,
    )
    db.add(achievement)
    await db.commit()
    await log_audit(db, actor_id=current_user.id, action=AuditAction.create, model_name="AchievementApplication", record_id=achievement.id, request_path="/achievements", request_method="POST", new_data={"title": title, "type": type.value})
    return {"id": achievement.id, "message": "Achievement submitted"}


@router.get("/achievements")
async def list_achievements(
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
    status_filter: AchievementStatus | None = None,
    type_filter: AchievementType | None = None,
    student_id: int | None = None,
):
    query = select(AchievementApplication)
    if status_filter is not None:
        query = query.where(AchievementApplication.status == status_filter)
    if type_filter is not None:
        query = query.where(AchievementApplication.type == type_filter)
    if student_id is not None:
        query = query.where(AchievementApplication.student_id == student_id)
    result = await db.execute(query.order_by(AchievementApplication.submitted_at.desc()))
    return {"items": [_serialize_model(record) for record in result.scalars().all()]}


@router.get("/achievements/my")
async def my_achievements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    student = await _student_profile_or_404(db, current_user.id)
    result = await db.execute(select(AchievementApplication).where(AchievementApplication.student_id == student.id).order_by(AchievementApplication.submitted_at.desc()))
    return {"items": [_serialize_model(record) for record in result.scalars().all()]}


@router.get("/achievements/{achievement_id}")
async def achievement_detail(
    achievement_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AchievementApplication).where(AchievementApplication.id == achievement_id))
    achievement = result.scalar_one_or_none()
    if achievement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Achievement not found")
    if current_user.role == UserRole.student:
        student = await _student_profile_or_404(db, current_user.id)
        if student.id != achievement.student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return _serialize_model(achievement)


@router.put("/achievements/{achievement_id}/approve")
async def approve_achievement(
    achievement_id: int,
    payload: AchievementReviewPayload,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AchievementApplication).where(AchievementApplication.id == achievement_id))
    achievement = result.scalar_one_or_none()
    if achievement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Achievement not found")
    achievement.status = AchievementStatus.approved
    achievement.points_approved = clamp(payload.points_approved or achievement.points_claimed, 0.0, ACHIEVEMENT_LIMITS[achievement.type])
    achievement.admin_note = payload.admin_note
    achievement.reviewed_by_id = current_user.id
    achievement.reviewed_at = datetime.utcnow()
    db.add(achievement)
    await db.commit()
    semester, academic_year = await _resolve_scope(db, achievement.semester_id)
    await _recalculate_and_refresh(db, achievement.student_id, semester.id, academic_year.id, actor_id=current_user.id, reason="achievement approved")
    return {"message": "Achievement approved"}


@router.put("/achievements/{achievement_id}/reject")
async def reject_achievement(
    achievement_id: int,
    payload: AchievementReviewPayload,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AchievementApplication).where(AchievementApplication.id == achievement_id))
    achievement = result.scalar_one_or_none()
    if achievement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Achievement not found")
    achievement.status = AchievementStatus.rejected
    achievement.admin_note = payload.admin_note
    achievement.reviewed_by_id = current_user.id
    achievement.reviewed_at = datetime.utcnow()
    db.add(achievement)
    await db.commit()
    semester, academic_year = await _resolve_scope(db, achievement.semester_id)
    await _recalculate_and_refresh(db, achievement.student_id, semester.id, academic_year.id, actor_id=current_user.id, reason="achievement rejected")
    return {"message": "Achievement rejected"}


@router.delete("/achievements/{achievement_id}")
async def delete_achievement(
    achievement_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AchievementApplication).where(AchievementApplication.id == achievement_id))
    achievement = result.scalar_one_or_none()
    if achievement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Achievement not found")
    if current_user.role == UserRole.student:
        student = await _student_profile_or_404(db, current_user.id)
        if student.id != achievement.student_id or achievement.status != AchievementStatus.pending:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete this achievement")
    await db.delete(achievement)
    await db.commit()
    return {"message": "Achievement deleted"}


@router.post("/feedback")
async def create_feedback(
    payload: FeedbackCreatePayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.mentor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    current_semester = await get_current_semester(db)
    feedback = FeedbackEntry(
        mentor_id=current_user.id,
        student_id=payload.student_id,
        course_id=payload.course_id,
        semester_id=current_semester.id if current_semester else None,
        type=payload.type,
        content=payload.content,
        sentiment=payload.sentiment,
        is_visible_to_student=payload.is_visible_to_student,
    )
    db.add(feedback)
    await db.commit()
    return {"id": feedback.id, "message": "Feedback created"}


@router.get("/feedback/student/{student_id}")
async def student_feedback(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _student_access_or_404(current_user, student_id, db)
    result = await db.execute(select(FeedbackEntry).where(FeedbackEntry.student_id == student_id).order_by(FeedbackEntry.created_at.desc()))
    return {"items": [_serialize_model(record) for record in result.scalars().all()]}


@router.get("/feedback/my-given")
async def my_given_feedback(
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.mentor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FeedbackEntry).where(FeedbackEntry.mentor_id == current_user.id).order_by(FeedbackEntry.created_at.desc()))
    return {"items": [_serialize_model(record) for record in result.scalars().all()]}


@router.put("/feedback/{feedback_id}")
async def update_feedback(
    feedback_id: int,
    payload: FeedbackUpdatePayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.mentor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FeedbackEntry).where(FeedbackEntry.id == feedback_id))
    feedback = result.scalar_one_or_none()
    if feedback is None or feedback.mentor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(feedback, field, value)
    db.add(feedback)
    await db.commit()
    return {"message": "Feedback updated"}


@router.delete("/feedback/{feedback_id}")
async def delete_feedback(
    feedback_id: int,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.mentor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FeedbackEntry).where(FeedbackEntry.id == feedback_id))
    feedback = result.scalar_one_or_none()
    if feedback is None or feedback.mentor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    await db.delete(feedback)
    await db.commit()
    return {"message": "Feedback deleted"}


@router.post("/tutor-ratings")
async def upsert_tutor_rating(
    payload: TutorRatingPayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.mentor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    current_semester = await get_current_semester(db)
    current_academic_year = await get_current_academic_year(db)
    if current_semester is None or current_academic_year is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current scope not available")
    semester = payload.semester or current_semester.number
    year = payload.year or current_academic_year.id
    total = clamp(payload.corporate_culture + payload.social_activity + payload.soft_skills + payload.discipline + payload.dorm_activity, 0.0, 5.0)
    result = await db.execute(
        select(TutorRating).where(
            TutorRating.mentor_id == current_user.id,
            TutorRating.student_id == payload.student_id,
            TutorRating.semester == semester,
            TutorRating.year == year,
        )
    )
    rating = result.scalar_one_or_none()
    if rating is None:
        rating = TutorRating(mentor_id=current_user.id, student_id=payload.student_id, semester=semester, year=year)
    rating.corporate_culture = clamp(payload.corporate_culture, 0.0, 1.0)
    rating.social_activity = clamp(payload.social_activity, 0.0, 1.0)
    rating.soft_skills = clamp(payload.soft_skills, 0.0, 1.0)
    rating.discipline = clamp(payload.discipline, 0.0, 1.0)
    rating.dorm_activity = clamp(payload.dorm_activity, 0.0, 1.0)
    rating.total = total
    rating.note = payload.note
    db.add(rating)
    await db.commit()
    return {"id": rating.id, "total": rating.total}


@router.get("/tutor-ratings/{student_id}")
async def tutor_ratings(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _student_access_or_404(current_user, student_id, db)
    result = await db.execute(select(TutorRating).where(TutorRating.student_id == student_id).order_by(TutorRating.created_at.desc()))
    return {"items": [_serialize_model(record) for record in result.scalars().all()]}


@router.post("/penalties")
async def create_penalty(
    payload: PenaltyCreatePayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.mentor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    semester, academic_year = await _resolve_scope(db, payload.semester_id)
    penalty = Penalty(
        student_id=payload.student_id,
        semester_id=semester.id,
        amount=-abs(int(payload.points)),
        covered_amount=0,
        comment=f"{payload.type}: {payload.reason}",
        status=PenaltyStatus.active,
        created_by_id=current_user.id,
    )
    db.add(penalty)
    await db.commit()
    await _recalculate_and_refresh(db, payload.student_id, semester.id, academic_year.id, actor_id=current_user.id, reason=payload.reason)
    return {"id": penalty.id, "message": "Penalty created"}


@router.get("/penalties/{student_id}")
async def list_penalties(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _student_access_or_404(current_user, student_id, db)
    result = await db.execute(select(Penalty).where(Penalty.student_id == student_id).order_by(Penalty.created_at.desc()))
    return {"items": [_serialize_model(record) for record in result.scalars().all()]}


@router.post("/penalties/recovery")
async def create_recovery_task(
    payload: RecoveryTaskPayload,
    current_user: User = Depends(require_role(UserRole.tutor, UserRole.mentor, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    semester, academic_year = await _resolve_scope(db, payload.semester_id)
    task = RecoveryTask(
        student_id=payload.student_id,
        assigned_by_id=current_user.id,
        semester_id=semester.id,
        task_description=payload.task_description,
        points_recoverable=clamp(payload.points_recoverable, 0.0, 10.0),
        status="pending",
        due_date=payload.due_date,
    )
    db.add(task)
    await db.commit()
    return {"id": task.id, "message": "Recovery task created"}


@router.put("/penalties/recovery/{task_id}/complete")
async def complete_recovery_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(RecoveryTask).where(RecoveryTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery task not found")
    student = await _student_profile_or_404(db, task.student_id)
    if current_user.role == UserRole.student and student.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    db.add(task)
    await db.commit()
    return {"message": "Recovery task marked complete"}


@router.put("/penalties/recovery/{task_id}/verify")
async def verify_recovery_task(
    task_id: int,
    points_recovered: float = Body(..., ge=0),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(RecoveryTask).where(RecoveryTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery task not found")
    task.status = "verified"
    task.points_recovered = clamp(points_recovered, 0.0, task.points_recoverable)
    task.verified_at = datetime.utcnow()
    db.add(task)
    await db.commit()
    semester, academic_year = await _resolve_scope(db, task.semester_id)
    await _recalculate_and_refresh(db, task.student_id, semester.id, academic_year.id, actor_id=current_user.id, reason="recovery verified")
    return {"message": "Recovery task verified"}


@router.post("/employment")
async def create_employment(
    payload: EmploymentPayload,
    document: UploadFile | None = File(None),
    current_user: User = Depends(require_role(UserRole.student, UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    student = await _student_profile_or_404(db, current_user.id if current_user.role == UserRole.student else payload.student_id)
    document_url = await _save_upload(document, "employment") if document else None
    employment = EmploymentRecord(
        student_id=student.id,
        company_name=payload.company_name,
        position=payload.position,
        type=payload.type.value,
        hours_per_week=payload.hours_per_week,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_it_related=payload.is_it_related,
        bonus_points=clamp(payload.bonus_points, 0.0, 10.0),
        verified=False,
        document_url=document_url,
        semester_id=payload.semester_id,
        semester=payload.semester,
        year=payload.year,
    )
    db.add(employment)
    await db.commit()
    return {"id": employment.id, "message": "Employment submitted"}


@router.get("/employment/my")
async def my_employment(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    student = await _student_profile_or_404(db, current_user.id)
    result = await db.execute(select(EmploymentRecord).where(EmploymentRecord.student_id == student.id).order_by(EmploymentRecord.created_at.desc()))
    return {"items": [_serialize_model(record) for record in result.scalars().all()]}


@router.get("/employment")
async def list_employment(
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EmploymentRecord).order_by(EmploymentRecord.created_at.desc()))
    return {"items": [record.__dict__ for record in result.scalars().all()]}


@router.put("/employment/{employment_id}/verify")
async def verify_employment(
    employment_id: int,
    bonus_points: float = Body(..., ge=0),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EmploymentRecord).where(EmploymentRecord.id == employment_id))
    employment = result.scalar_one_or_none()
    if employment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employment not found")
    employment.verified = True
    employment.bonus_points = clamp(bonus_points, 0.0, 10.0)
    db.add(employment)
    await db.commit()
    semester, academic_year = await _resolve_scope(db, employment.semester_id)
    await _recalculate_and_refresh(db, employment.student_id, semester.id, academic_year.id, actor_id=current_user.id, reason="employment verified")
    return {"message": "Employment verified"}


@router.get("/admin/dashboard")
async def admin_dashboard(
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    total_students = (await db.execute(select(func.count()).select_from(StudentProfile))).scalar_one()
    grant_eligible = (await db.execute(select(func.count()).select_from(RankingSnapshot).where(RankingSnapshot.total_points >= 80))).scalar_one()
    avg_score = (await db.execute(select(func.coalesce(func.avg(RankingSnapshot.total_points), 0.0)))).scalar_one()
    return {"total_students": total_students, "grant_eligible": grant_eligible, "average_score": float(avg_score or 0.0)}


@router.get("/admin/audit-log")
async def audit_log(
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    result = await db.execute(query.offset((page - 1) * size).limit(size))
    return {"items": [_serialize_model(record) for record in result.scalars().all()], "page": page, "size": size, "total": total}


@router.post("/admin/users")
async def admin_create_user(
    payload: UserCreatePayload,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    from app.services.auth_service import AuthService

    user, username, password = await AuthService.provision_admin_user(
        db=db,
        full_name=payload.full_name,
        role=payload.role,
        username=payload.username,
        password=payload.password,
        phone=payload.phone,
        student_code=payload.student_code,
        group_id=payload.current_group_id,
        academic_year_id=payload.admission_year,
    )
    response = _serialize_user(user)
    response["generated_password"] = password
    response["generated_username"] = username
    await log_audit(db, actor_id=current_user.id, action=AuditAction.create, model_name="User", record_id=user.id, request_path="/admin/users", request_method="POST", new_data={**payload.model_dump(), "username": username})
    return response


@router.put("/admin/users/{user_id}/toggle")
async def admin_toggle_user(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = not user.is_active
    db.add(user)
    await db.commit()
    return _serialize_user(user)


@router.get("/admin/reports/grant")
async def grant_report(
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    academic_year = await get_current_academic_year(db)
    if academic_year is None:
        return {"items": []}
    leaderboard = await get_year_leaderboard(db, academic_year.id)
    return {"items": leaderboard}


@router.post("/admin/recalculate-all")
async def recalculate_all(
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    semester = await get_current_semester(db)
    academic_year = await get_current_academic_year(db)
    if semester is None or academic_year is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current scope not available")
    result = await db.execute(select(StudentProfile.id))
    student_ids = [row[0] for row in result.all()]
    for student_id in student_ids:
        await _recalculate_and_refresh(db, student_id, semester.id, academic_year.id, actor_id=current_user.id, reason="bulk recalculation")
    return {"recalculated": len(student_ids)}


@router.post("/admin/notifications/send")
async def send_notification(
    payload: NotificationPayload,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    notification = await create_notification(db, user_id=payload.user_id, title=payload.title, message=payload.message, notification_type=payload.type)
    return {"id": notification.id, "message": "Notification sent"}


@router.get("/users")
async def list_users(
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
    role: UserRole | None = None,
    search: str | None = None,
):
    query = select(User)
    if role is not None:
        query = query.where(User.role == role)
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(or_(func.lower(User.full_name).like(pattern), func.lower(User.username).like(pattern)))
    result = await db.execute(query.order_by(User.full_name))
    return {"items": [_serialize_user(user) for user in result.scalars().all()]}


@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in {UserRole.admin, UserRole.super_admin} and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _serialize_user(user)


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    payload: UserUpdatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in {UserRole.admin, UserRole.super_admin} and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.add(user)
    await db.commit()
    return _serialize_user(user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await db.delete(user)
    await db.commit()
    return {"message": "User deleted"}


@router.get("/groups")
async def list_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Group).order_by(Group.name))
    return {"items": [_serialize_model(row) for row in result.scalars().all()]}


@router.post("/groups")
async def create_group(
    payload: GroupPayload,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    group = Group(name=payload.name, course=payload.course, academic_year_id=payload.academic_year_id)
    db.add(group)
    await db.commit()
    return {"id": group.id, "message": "Group created"}


@router.get("/academic-years")
async def list_academic_years(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AcademicYear).order_by(AcademicYear.start_date.desc()))
    return {"items": [_serialize_model(row) for row in result.scalars().all()]}


@router.post("/academic-years")
async def create_academic_year(
    payload: AcademicYearPayload,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    if payload.is_current:
        await db.execute(update(AcademicYear).values(is_current=False))
    academic_year = AcademicYear(name=payload.name, start_date=payload.start_date, end_date=payload.end_date, is_current=payload.is_current)
    db.add(academic_year)
    await db.commit()
    return {"id": academic_year.id, "message": "Academic year created"}


@router.put("/academic-years/{academic_year_id}")
async def update_academic_year(
    academic_year_id: int,
    payload: AcademicYearPayload,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    academic_year = (await db.execute(select(AcademicYear).where(AcademicYear.id == academic_year_id))).scalar_one_or_none()
    if academic_year is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")
    academic_year.name = payload.name
    academic_year.start_date = payload.start_date
    academic_year.end_date = payload.end_date
    academic_year.is_current = payload.is_current
    db.add(academic_year)
    await db.commit()
    return {"message": "Academic year updated"}


@router.get("/semesters")
async def list_semesters(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Semester).order_by(Semester.start_date.desc()))
    return {"items": [_serialize_model(row) for row in result.scalars().all()]}


@router.post("/semesters")
async def create_semester(
    payload: SemesterPayload,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin)),
    db: AsyncSession = Depends(get_db),
):
    if payload.is_current:
        await db.execute(update(Semester).values(is_current=False))
    semester = Semester(
        academic_year_id=payload.academic_year_id,
        number=payload.number,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_current=payload.is_current,
    )
    db.add(semester)
    await db.commit()
    return {"id": semester.id, "message": "Semester created"}


@router.post("/courses")
async def create_course(
    payload: CoursePayload,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.super_admin, UserRole.tutor, UserRole.mentor)),
    db: AsyncSession = Depends(get_db),
):
    course = Course(name=payload.name, code=payload.code, mentor_id=payload.mentor_id, year=payload.year, semester=payload.semester, max_hours=payload.max_hours)
    db.add(course)
    await db.commit()
    return {"id": course.id, "message": "Course created"}


@router.get("/courses")
async def list_courses(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Course).order_by(Course.name))
    return {"items": [_serialize_model(row) for row in result.scalars().all()]}


@router.get("/parent/children")
async def parent_children(
    current_user: User = Depends(require_role(UserRole.parent)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ParentProfile).where(ParentProfile.user_id == current_user.id))
    parent = result.scalar_one_or_none()
    if parent is None:
        return {"items": []}
    query = (
        select(StudentParentLink, StudentProfile, User, Group)
        .join(StudentProfile, StudentParentLink.student_id == StudentProfile.id)
        .join(User, User.id == StudentProfile.user_id)
        .outerjoin(Group, Group.id == StudentProfile.current_group_id)
        .where(StudentParentLink.parent_id == parent.id, StudentParentLink.is_active.is_(True))
    )
    result = await db.execute(query.order_by(User.full_name))
    items: list[dict[str, Any]] = []
    for link, student, user, group in result.all():
        items.append(
            {
                "student_id": student.id,
                "full_name": user.full_name,
                "username": user.username,
                "student_code": student.student_code,
                "current_group_id": student.current_group_id,
                "current_group_name": getattr(group, "name", None),
                "admission_year": student.admission_year,
                "is_active": user.is_active,
            }
        )
    return {"items": items}


@router.get("/parent/children/{student_id}/ranks")
async def parent_child_ranks(
    student_id: int,
    current_user: User = Depends(require_role(UserRole.parent)),
    db: AsyncSession = Depends(get_db),
    academic_year_id: int | None = None,
):
    # ensure parent has access to student
    student = await _student_access_or_404(current_user, student_id, db)
    if academic_year_id is None:
        academic_year = await get_current_academic_year(db)
        if academic_year is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")
        academic_year_id = academic_year.id

    leaderboard = await get_year_leaderboard(db, academic_year_id)
    overall = next((item for item in leaderboard if item["student_id"] == student.id), None)
    overall_rank = overall["rank"] if overall is not None else None
    overall_points = overall["total_points"] if overall is not None else None

    group_rank = None
    group_count = 0
    if student.current_group_id:
        result = await db.execute(
            select(
                RankingSnapshot.student_id,
                StudentProfile.student_code,
                func.sum(RankingSnapshot.total_points).label("total_points"),
            )
            .join(StudentProfile, StudentProfile.id == RankingSnapshot.student_id)
            .where(RankingSnapshot.academic_year_id == academic_year_id, StudentProfile.current_group_id == student.current_group_id)
            .group_by(RankingSnapshot.student_id, StudentProfile.student_code)
            .order_by(func.sum(RankingSnapshot.total_points).desc(), func.sum(RankingSnapshot.work_points).desc(), func.sum(RankingSnapshot.academic_points).desc())
        )
        rows = result.all()
        group_count = len(rows)
        for idx, row in enumerate(rows, start=1):
            if row.student_id == student.id:
                group_rank = idx
                break

    course_rank = None
    course_count = 0
    # try to compute course (year of study) rank if group information available
    if student.current_group_id:
        group_row = (await db.execute(select(Group).where(Group.id == student.current_group_id))).scalar_one_or_none()
        if group_row is not None:
            course_number = group_row.course
            result = await db.execute(
                select(
                    RankingSnapshot.student_id,
                    StudentProfile.student_code,
                    func.sum(RankingSnapshot.total_points).label("total_points"),
                )
                .join(StudentProfile, StudentProfile.id == RankingSnapshot.student_id)
                .join(Group, Group.id == StudentProfile.current_group_id)
                .where(RankingSnapshot.academic_year_id == academic_year_id, Group.course == course_number)
                .group_by(RankingSnapshot.student_id, StudentProfile.student_code)
                .order_by(func.sum(RankingSnapshot.total_points).desc(), func.sum(RankingSnapshot.work_points).desc(), func.sum(RankingSnapshot.academic_points).desc())
            )
            rows = result.all()
            course_count = len(rows)
            for idx, row in enumerate(rows, start=1):
                if row.student_id == student.id:
                    course_rank = idx
                    break

    return {
        "student_id": student.id,
        "overall_rank": overall_rank,
        "overall_points": overall_points,
        "university_total": len(leaderboard),
        "group_rank": group_rank,
        "group_total": group_count,
        "course_rank": course_rank,
        "course_total": course_count,
    }
