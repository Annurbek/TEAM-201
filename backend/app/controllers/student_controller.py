"""Student controller — business logic for student endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AcademicYear,
    AchievementApplication,
    AttendanceRecord,
    FeedbackEntry,
    GradeRecord,
    Group,
    Penalty,
    RankingSnapshot,
    RecoveryTask,
    ScoreHistoryLog,
    Semester,
    StudentProfile,
    User,
)
from app.services.audit_service import log_audit
from app.services.edumetric_service import (
    check_student_access,
    get_student_profile_or_404,
    recalculate_and_refresh,
    resolve_scope,
    serialize_model,
    serialize_user,
)
from app.services.score_service import (
    calculate_student_score,
    get_current_academic_year,
    get_current_semester,
    get_year_leaderboard,
)


async def list_students(
    db: AsyncSession,
    search: str | None = None,
    group_id: int | None = None,
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    from sqlalchemy import or_ as sa_or

    query = select(StudentProfile, User).join(User, User.id == StudentProfile.user_id)
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            sa_or(
                func.lower(User.full_name).like(pattern),
                func.lower(User.username).like(pattern),
                func.lower(StudentProfile.student_code).like(pattern),
            )
        )
    if group_id is not None:
        query = query.where(StudentProfile.current_group_id == group_id)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    result = await db.execute(query.order_by(User.full_name).offset((page - 1) * size).limit(size))
    items = []
    for student, user in result.all():
        items.append({
            "student_id": student.id,
            **serialize_user(user),
            "student_code": student.student_code,
            "current_group_id": student.current_group_id,
            "admission_year": student.admission_year,
        })
    return {"items": items, "page": page, "size": size, "total": total}


async def get_student_detail(
    current_user: User,
    student_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    student = await check_student_access(current_user, student_id, db)
    user = (await db.execute(select(User).where(User.id == student.user_id))).scalar_one()
    semester = await get_current_semester(db)
    academic_year = await get_current_academic_year(db)
    score = None
    if semester and academic_year:
        score = await calculate_student_score(db, student.id, semester.id, academic_year.id)
    return {
        "student": {
            "student_id": student.id,
            **serialize_user(user),
            "student_code": student.student_code,
            "current_group_id": student.current_group_id,
            "admission_year": student.admission_year,
        },
        "score": score,
    }


async def get_student_score(
    current_user: User,
    student_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    await check_student_access(current_user, student_id, db)
    semester = await get_current_semester(db)
    academic_year = await get_current_academic_year(db)
    if semester is None or academic_year is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current scope not available")
    return await calculate_student_score(db, student_id, semester.id, academic_year.id)


async def get_student_score_history(
    current_user: User,
    student_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    await check_student_access(current_user, student_id, db)
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


async def get_student_feed(
    current_user: User,
    student_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    await check_student_access(current_user, student_id, db)
    items: list[dict[str, Any]] = []

    for table, label, time_col in [
        (AttendanceRecord, "attendance", "created_at"),
        (GradeRecord, "grade", "created_at"),
        (AchievementApplication, "achievement", "submitted_at"),
        (FeedbackEntry, "feedback", "created_at"),
        (Penalty, "penalty", "created_at"),
        (RecoveryTask, "recovery", "created_at"),
    ]:
        order_col = getattr(table, time_col)
        result = await db.execute(select(table).where(table.student_id == student_id).order_by(order_col.desc()))
        for record in result.scalars().all():
            ts = getattr(record, "created_at", None) or getattr(record, "submitted_at", None)
            items.append({"type": label, "created_at": ts, "data": record})

    result = await db.execute(
        select(ScoreHistoryLog).where(ScoreHistoryLog.student_id == student_id).order_by(ScoreHistoryLog.created_at.desc())
    )
    for record in result.scalars().all():
        items.append({"type": "score_history", "created_at": record.created_at, "data": record})

    items.sort(key=lambda item: item["created_at"] or datetime.min, reverse=True)
    return {"items": items}


async def recalculate_student(
    current_user: User,
    student_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    semester = await get_current_semester(db)
    academic_year = await get_current_academic_year(db)
    if semester is None or academic_year is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current scope not available")
    score = await recalculate_and_refresh(
        db, student_id, semester.id, academic_year.id,
        actor_id=current_user.id, reason="manual recalculation",
    )
    await log_audit(
        db, actor_id=current_user.id, action="update", model_name="RankingSnapshot",
        record_id=score["snapshot_id"], request_path="/students/{student_id}/recalculate",
        request_method="POST", new_data=score,
    )
    return score
