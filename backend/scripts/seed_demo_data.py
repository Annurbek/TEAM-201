from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.database import AsyncSessionLocal
from app.models import (
    AcademicScore,
    AcademicYear,
    AttendanceScore,
    AuditAction,
    AuditLog,
    Certificate,
    DisciplineScore,
    Group,
    ParentProfile,
    Penalty,
    PenaltyCoverage,
    PenaltyStatus,
    Project,
    RankingSnapshot,
    ReviewStatus,
    ScoreHistoryLog,
    Semester,
    StudentGroupMembership,
    StudentParentLink,
    StudentProfile,
    TutorGroupLink,
    TutorProfile,
    TutorScore,
    User,
    UserRole,
    WorkScore,
    WorkType,
)


DEMO_DOMAIN = "demo.local"
DEMO_PASSWORD = "DemoPass123!"
DEMO_ACADEMIC_YEAR = "2025-2026 Demo"
PASSWORD_HASH_ITERATIONS = 210_000


@dataclass(frozen=True)
class DemoUserSpec:
    full_name: str
    username: str
    role: UserRole
    phone: str | None = None


def _encode_base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def get_password_hash(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return (
        f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}$"
        f"{_encode_base64url(salt)}${_encode_base64url(digest)}"
    )


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await clear_demo_data(session)
        summary = await seed_demo_data(session)
        await session.commit()

    print("Demo data seeded successfully.")
    print(f"Default demo password: {DEMO_PASSWORD}")
    for key, value in summary.items():
        print(f"{key}: {value}")


async def clear_demo_data(session: AsyncSession) -> None:
    user_ids = list(
        await session.scalars(select(User.id).where(User.username.like(f"%")))
    )
    academic_year_ids = list(
        await session.scalars(
            select(AcademicYear.id).where(AcademicYear.name == DEMO_ACADEMIC_YEAR)
        )
    )

    student_ids: list[int] = []
    parent_ids: list[int] = []
    tutor_ids: list[int] = []
    group_ids: list[int] = []
    semester_ids: list[int] = []

    if user_ids:
        student_ids = list(
            await session.scalars(
                select(StudentProfile.id).where(StudentProfile.user_id.in_(user_ids))
            )
        )
        parent_ids = list(
            await session.scalars(
                select(ParentProfile.id).where(ParentProfile.user_id.in_(user_ids))
            )
        )
        tutor_ids = list(
            await session.scalars(
                select(TutorProfile.id).where(TutorProfile.user_id.in_(user_ids))
            )
        )

    if academic_year_ids:
        group_ids = list(
            await session.scalars(
                select(Group.id).where(Group.academic_year_id.in_(academic_year_ids))
            )
        )
        semester_ids = list(
            await session.scalars(
                select(Semester.id).where(Semester.academic_year_id.in_(academic_year_ids))
            )
        )

    penalty_ids = await _select_penalty_ids(session, student_ids, semester_ids, user_ids)

    if penalty_ids or user_ids:
        filters = []
        if penalty_ids:
            filters.append(PenaltyCoverage.penalty_id.in_(penalty_ids))
        if user_ids:
            filters.append(PenaltyCoverage.covered_by_id.in_(user_ids))
        await session.execute(delete(PenaltyCoverage).where(or_(*filters)))

    await _delete_by_filters(session, Penalty, student_ids, semester_ids, user_ids)
    await _delete_by_filters(session, WorkScore, student_ids, semester_ids, user_ids)
    await _delete_by_filters(session, TutorScore, student_ids, semester_ids, None, tutor_ids)
    await _delete_by_filters(session, DisciplineScore, student_ids, semester_ids, user_ids)
    await _delete_by_filters(session, Project, student_ids, semester_ids, user_ids)
    await _delete_by_filters(session, Certificate, student_ids, semester_ids, user_ids)
    await _delete_by_filters(session, AttendanceScore, student_ids, semester_ids)
    await _delete_by_filters(session, AcademicScore, student_ids, semester_ids)
    await _delete_by_filters(session, RankingSnapshot, student_ids, semester_ids)

    if student_ids or user_ids:
        filters = []
        if student_ids:
            filters.append(ScoreHistoryLog.student_id.in_(student_ids))
        if user_ids:
            filters.append(ScoreHistoryLog.actor_id.in_(user_ids))
        await session.execute(delete(ScoreHistoryLog).where(or_(*filters)))

    if user_ids:
        await session.execute(delete(AuditLog).where(AuditLog.actor_id.in_(user_ids)))

    if student_ids or parent_ids:
        filters = []
        if student_ids:
            filters.append(StudentParentLink.student_id.in_(student_ids))
        if parent_ids:
            filters.append(StudentParentLink.parent_id.in_(parent_ids))
        await session.execute(delete(StudentParentLink).where(or_(*filters)))

    if student_ids or group_ids:
        filters = []
        if student_ids:
            filters.append(StudentGroupMembership.student_id.in_(student_ids))
        if group_ids:
            filters.append(StudentGroupMembership.group_id.in_(group_ids))
        await session.execute(delete(StudentGroupMembership).where(or_(*filters)))

    if tutor_ids or group_ids:
        filters = []
        if tutor_ids:
            filters.append(TutorGroupLink.tutor_id.in_(tutor_ids))
        if group_ids:
            filters.append(TutorGroupLink.group_id.in_(group_ids))
        await session.execute(delete(TutorGroupLink).where(or_(*filters)))

    if student_ids:
        await session.execute(delete(StudentProfile).where(StudentProfile.id.in_(student_ids)))
    if parent_ids:
        await session.execute(delete(ParentProfile).where(ParentProfile.id.in_(parent_ids)))
    if tutor_ids:
        await session.execute(delete(TutorProfile).where(TutorProfile.id.in_(tutor_ids)))
    if group_ids:
        await session.execute(delete(Group).where(Group.id.in_(group_ids)))
    if semester_ids:
        await session.execute(delete(Semester).where(Semester.id.in_(semester_ids)))
    if academic_year_ids:
        await session.execute(delete(AcademicYear).where(AcademicYear.id.in_(academic_year_ids)))
    if user_ids:
        await session.execute(delete(User).where(User.id.in_(user_ids)))

    await session.flush()


async def _select_penalty_ids(
    session: AsyncSession,
    student_ids: list[int],
    semester_ids: list[int],
    user_ids: list[int],
) -> list[int]:
    filters = []
    if student_ids:
        filters.append(Penalty.student_id.in_(student_ids))
    if semester_ids:
        filters.append(Penalty.semester_id.in_(semester_ids))
    if user_ids:
        filters.append(Penalty.created_by_id.in_(user_ids))

    if not filters:
        return []

    return list(await session.scalars(select(Penalty.id).where(or_(*filters))))


async def _delete_by_filters(
    session: AsyncSession,
    model,
    student_ids: list[int] | None = None,
    semester_ids: list[int] | None = None,
    user_ids: list[int] | None = None,
    tutor_ids: list[int] | None = None,
) -> None:
    filters = []
    if student_ids and hasattr(model, "student_id"):
        filters.append(model.student_id.in_(student_ids))
    if semester_ids and hasattr(model, "semester_id"):
        filters.append(model.semester_id.in_(semester_ids))
    if user_ids:
        if hasattr(model, "updated_by_id"):
            filters.append(model.updated_by_id.in_(user_ids))
        if hasattr(model, "reviewed_by_id"):
            filters.append(model.reviewed_by_id.in_(user_ids))
        if hasattr(model, "created_by_id"):
            filters.append(model.created_by_id.in_(user_ids))
    if tutor_ids and hasattr(model, "tutor_id"):
        filters.append(model.tutor_id.in_(tutor_ids))

    if filters:
        await session.execute(delete(model).where(or_(*filters)))


async def seed_demo_data(session: AsyncSession) -> dict[str, int]:
    now = datetime.utcnow()
    password_hash = get_password_hash(DEMO_PASSWORD)

    users = [
        User(
            full_name=spec.full_name,
            username=spec.username,
            phone=spec.phone,
            password_hash=password_hash,
            role=spec.role,
            is_active=True,
        )
        for spec in build_user_specs()
    ]
    session.add_all(users)
    await session.flush()

    admin_user = next(user for user in users if user.username == f"demo.admin")
    tutor_users = [user for user in users if user.role == UserRole.tutor]
    parent_users = [user for user in users if user.role == UserRole.parent]
    student_users = [user for user in users if user.role == UserRole.student]

    academic_year = AcademicYear(
        name=DEMO_ACADEMIC_YEAR,
        start_date=datetime(2025, 9, 1),
        end_date=datetime(2026, 6, 30),
        is_current=True,
    )
    session.add(academic_year)
    await session.flush()

    semesters = [
        Semester(
            academic_year_id=academic_year.id,
            number=1,
            start_date=datetime(2025, 9, 1),
            end_date=datetime(2026, 1, 31),
            is_current=False,
        ),
        Semester(
            academic_year_id=academic_year.id,
            number=2,
            start_date=datetime(2026, 2, 1),
            end_date=datetime(2026, 6, 30),
            is_current=True,
        ),
    ]
    session.add_all(semesters)
    await session.flush()
    current_semester = semesters[1]

    groups = [
        Group(name="DEMO-101", course=1, academic_year_id=academic_year.id),
        Group(name="DEMO-201", course=2, academic_year_id=academic_year.id),
        Group(name="DEMO-301", course=3, academic_year_id=academic_year.id),
    ]
    session.add_all(groups)
    await session.flush()

    tutors = [TutorProfile(user_id=user.id) for user in tutor_users]
    parents = [ParentProfile(user_id=user.id) for user in parent_users]
    session.add_all([*tutors, *parents])
    await session.flush()

    students = [
        StudentProfile(
            user_id=user.id,
            student_code=f"DEMO-ST-{index:03d}",
            current_group_id=groups[(index - 1) % len(groups)].id,
            admission_year=2025,
        )
        for index, user in enumerate(student_users, start=1)
    ]
    session.add_all(students)
    await session.flush()

    session.add_all(
        [
            StudentParentLink(
                student_id=student.id,
                parent_id=parents[index % len(parents)].id,
                is_active=True,
            )
            for index, student in enumerate(students)
        ]
    )
    session.add_all(
        [
            StudentGroupMembership(
                student_id=student.id,
                group_id=groups[index % len(groups)].id,
                academic_year_id=academic_year.id,
                joined_at=datetime(2025, 9, 1),
            )
            for index, student in enumerate(students)
        ]
    )
    session.add_all(
        [
            TutorGroupLink(
                tutor_id=tutor.id,
                group_id=groups[index % len(groups)].id,
                academic_year_id=academic_year.id,
            )
            for index, tutor in enumerate(tutors)
        ]
    )
    await session.flush()

    penalties: list[Penalty] = []
    rankings: list[RankingSnapshot] = []
    work_types = list(WorkType)

    for index, student in enumerate(students, start=1):
        academic_points = 55.0 + index
        attendance_points = 10.0 + (index % 5)
        certificate_points = 3.0 if index % 2 == 0 else 0.0
        project_points = 6.0 + (index % 4)
        discipline_points = 8.0
        tutor_points = 7.0 + (index % 3)
        work_points = float(index % 6)
        penalty_points = -float(index % 4)
        total_points = round(
            academic_points
            + attendance_points
            + certificate_points
            + project_points
            + discipline_points
            + tutor_points
            + work_points
            + penalty_points,
            2,
        )

        session.add_all(
            [
                AcademicScore(
                    student_id=student.id,
                    semester_id=current_semester.id,
                    average_gpa=3.2 + (index % 7) * 0.2,
                    percent=70 + index,
                    points=academic_points,
                ),
                AttendanceScore(
                    student_id=student.id,
                    semester_id=current_semester.id,
                    percent=82 + (index % 10),
                    points=attendance_points,
                ),
                Certificate(
                    student_id=student.id,
                    semester_id=current_semester.id,
                    title=f"Demo certificate {index}",
                    file_url=f"https://example.com/demo/certificates/{index}.pdf",
                    points=certificate_points,
                    status=ReviewStatus.approved,
                    reviewed_by_id=admin_user.id,
                    reviewed_at=now,
                ),
                Project(
                    student_id=student.id,
                    semester_id=current_semester.id,
                    title=f"Demo project {index}",
                    description="Demo project for ranking calculation.",
                    file_url=f"https://example.com/demo/projects/{index}.zip",
                    points=project_points,
                    status=ReviewStatus.approved,
                    reviewed_by_id=admin_user.id,
                    reviewed_at=now,
                ),
                DisciplineScore(
                    student_id=student.id,
                    semester_id=current_semester.id,
                    points=discipline_points,
                    comment="Demo discipline score.",
                    updated_by_id=admin_user.id,
                ),
                TutorScore(
                    student_id=student.id,
                    tutor_id=tutors[(index - 1) % len(tutors)].id,
                    semester_id=current_semester.id,
                    points=tutor_points,
                    comment="Demo tutor feedback.",
                ),
                WorkScore(
                    student_id=student.id,
                    semester_id=current_semester.id,
                    work_type=work_types[index % len(work_types)],
                    points=work_points,
                    updated_by_id=admin_user.id,
                ),
                ScoreHistoryLog(
                    student_id=student.id,
                    actor_id=admin_user.id,
                    field_name="total_points",
                    old_value=None,
                    new_value=str(total_points),
                    reason="Initial demo ranking seed.",
                ),
            ]
        )

        penalties.append(
            Penalty(
                student_id=student.id,
                semester_id=current_semester.id,
                amount=1 + (index % 5),
                covered_amount=1 if index % 3 == 0 else 0,
                comment="Demo penalty.",
                status=PenaltyStatus.partially_covered
                if index % 3 == 0
                else PenaltyStatus.active,
                created_by_id=admin_user.id,
            )
        )
        rankings.append(
            RankingSnapshot(
                student_id=student.id,
                semester_id=current_semester.id,
                academic_year_id=academic_year.id,
                academic_points=academic_points,
                attendance_points=attendance_points,
                certificate_points=certificate_points,
                project_points=project_points,
                discipline_points=discipline_points,
                tutor_points=tutor_points,
                work_points=work_points,
                penalty_points=penalty_points,
                total_points=total_points,
                rank_position=index,
            )
        )

    session.add_all([*penalties, *rankings])
    await session.flush()

    coverages = [
        PenaltyCoverage(
            penalty_id=penalty.id,
            covered_by_id=admin_user.id,
            amount=penalty.covered_amount,
        )
        for penalty in penalties
        if penalty.covered_amount > 0
    ]
    session.add_all(coverages)

    session.add_all(
        [
            AuditLog(
                actor_id=admin_user.id,
                action=AuditAction.create,
                model_name=model_name,
                record_id=None,
                request_path="/scripts/seed_demo_data.py",
                request_method="SEED",
                old_data=None,
                new_data="demo data",
            )
            for model_name in [
                "User",
                "StudentProfile",
                "AcademicScore",
                "Penalty",
                "RankingSnapshot",
            ]
        ]
    )

    await session.flush()

    return {
        "users": len(users),
        "students": len(students),
        "parents": len(parents),
        "tutors": len(tutors),
        "groups": len(groups),
        "semesters": len(semesters),
        "academic_years": 1,
        "academic_scores": len(students),
        "attendance_scores": len(students),
        "certificates": len(students),
        "projects": len(students),
        "discipline_scores": len(students),
        "tutor_scores": len(students),
        "work_scores": len(students),
        "penalties": len(penalties),
        "penalty_coverages": len(coverages),
        "ranking_snapshots": len(rankings),
        "score_history_logs": len(students),
        "audit_logs": 5,
    }


def build_user_specs() -> list[DemoUserSpec]:
    specs = [
        DemoUserSpec("Demo Super Admin", f"demo.superadmin", UserRole.super_admin, "+998900000001"),
        DemoUserSpec("Demo Admin", f"demo.admin", UserRole.admin, "+998900000002"),
    ]

    specs.extend(
        DemoUserSpec(
            full_name=f"Demo Tutor {index}",
            username=f"demo.tutor{index}",
            role=UserRole.tutor,
            phone=f"+9989000001{index:02d}",
        )
        for index in range(1, 4)
    )
    specs.extend(
        DemoUserSpec(
            full_name=f"Demo Parent {index}",
            username=f"demo.parent{index}",
            role=UserRole.parent,
            phone=f"+9989000002{index:02d}",
        )
        for index in range(1, 5)
    )
    specs.extend(
        DemoUserSpec(
            full_name=f"Demo Student {index}",
            username=f"demo.student{index}",
            role=UserRole.student,
            phone=f"+9989000003{index:02d}",
        )
        for index in range(1, 12)
    )

    return specs


async def print_table_counts() -> None:
    async with AsyncSessionLocal() as session:
        for model in [
            User,
            AcademicYear,
            Semester,
            Group,
            StudentProfile,
            ParentProfile,
            TutorProfile,
            StudentParentLink,
            StudentGroupMembership,
            TutorGroupLink,
            AcademicScore,
            AttendanceScore,
            Certificate,
            Project,
            DisciplineScore,
            TutorScore,
            WorkScore,
            Penalty,
            PenaltyCoverage,
            RankingSnapshot,
            ScoreHistoryLog,
            AuditLog,
        ]:
            count = await session.scalar(select(func.count()).select_from(model))
            print(f"{model.__tablename__}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
