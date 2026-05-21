from __future__ import annotations

import asyncio
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import delete, select

from app.db.base import Base
from app.db.database import AsyncSessionLocal, engine
from app.models import (
    AcademicYear,
    AchievementApplication,
    AchievementStatus,
    AchievementType,
    AttendanceRecord,
    AttendanceStatus,
    AttendanceScore,
    AuditLog,
    Certificate,
    Course,
    DisciplineScore,
    EmploymentRecord,
    FeedbackEntry,
    FeedbackType,
    GradeRecord,
    Group,
    Notification,
    ParentProfile,
    Penalty,
    PenaltyCoverage,
    PenaltyStatus,
    Project,
    RankingSnapshot,
    RecoveryTask,
    ScoreHistoryLog,
    Semester,
    StudentGroupMembership,
    StudentParentLink,
    StudentProfile,
    TutorGroupLink,
    TutorProfile,
    TutorRating,
    User,
    UserRole,
)
from app.models.scores import AcademicScore
from app.services.auth_service import AuthService
from app.services.score_service import calculate_student_score, recalculate_rankings

ADMIN_EMAIL = "admin@pdp.uz"
MENTOR_EMAILS = ["mentor1@pdp.uz", "mentor2@pdp.uz", "mentor3@pdp.uz"]
STUDENT_EMAILS = [f"student{i:02d}@pdp.uz" for i in range(1, 21)]
PARENT_EMAILS = [f"parent{i:02d}@pdp.uz" for i in range(1, 21)]
DEMO_PASSWORD = "DemoPass123!"

COURSE_NAMES = ["ITS", "Programming", "Website", "Full Stack", "BPM", "Big Data"]
MENTOR_COURSE_MAP = {
    "mentor1@pdp.uz": ["Programming", "Full Stack"],
    "mentor2@pdp.uz": ["ITS", "BPM"],
    "mentor3@pdp.uz": ["Website", "Big Data"],
}


async def reset_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)


async def clear_tables(session) -> None:
    for model in [
        AttendanceRecord,
        GradeRecord,
        AchievementApplication,
        FeedbackEntry,
        TutorRating,
        RecoveryTask,
        EmploymentRecord,
        PenaltyCoverage,
        Penalty,
        Certificate,
        Project,
        DisciplineScore,
        AttendanceScore,
        AcademicScore,
        RankingSnapshot,
        ScoreHistoryLog,
        Notification,
        TutorGroupLink,
        StudentGroupMembership,
        StudentParentLink,
        Group,
        Course,
        Semester,
        AcademicYear,
        TutorProfile,
        ParentProfile,
        StudentProfile,
        User,
        AuditLog,
    ]:
        await session.execute(delete(model))
    await session.commit()


async def create_users(session):
    admin = await AuthService.register_user(
        session,
        full_name="PDP Admin",
        email=ADMIN_EMAIL,
        password=DEMO_PASSWORD,
        role=UserRole.admin,
        phone="+998901111111",
    )

    mentors = []
    mentor_specs = [
        ("Mentor One", "mentor1@pdp.uz"),
        ("Mentor Two", "mentor2@pdp.uz"),
        ("Mentor Three", "mentor3@pdp.uz"),
    ]
    for full_name, email in mentor_specs:
        mentors.append(
            await AuthService.register_user(
                session,
                full_name=full_name,
                email=email,
                password=DEMO_PASSWORD,
                role=UserRole.tutor,
                phone=f"+99890{random.randint(1000000, 9999999)}",
            )
        )

    students = []
    for index, email in enumerate(STUDENT_EMAILS, start=1):
        students.append(
            await AuthService.register_user(
                session,
                full_name=f"Student {index:02d}",
                email=email,
                password=DEMO_PASSWORD,
                role=UserRole.student,
                phone=f"+99891{index:07d}",
                student_code=f"PDP-2025-{index:03d}",
            )
        )

    parents = []
    for index, email in enumerate(PARENT_EMAILS, start=1):
        parents.append(
            await AuthService.register_user(
                session,
                full_name=f"Parent {index:02d}",
                email=email,
                password=DEMO_PASSWORD,
                role=UserRole.parent,
                phone=f"+99893{index:07d}",
            )
        )

    await session.commit()
    return admin, mentors, students, parents


async def create_academic_structure(session, mentors):
    academic_year = AcademicYear(
        name="2025-2026",
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
            is_current=True,
        ),
        Semester(
            academic_year_id=academic_year.id,
            number=2,
            start_date=datetime(2026, 2, 1),
            end_date=datetime(2026, 6, 30),
            is_current=False,
        ),
    ]
    session.add_all(semesters)
    await session.flush()

    groups = [
        Group(name="CS-101", course=1, academic_year_id=academic_year.id),
        Group(name="CS-102", course=2, academic_year_id=academic_year.id),
    ]
    session.add_all(groups)
    await session.flush()

    mentor_map = {mentor.username: mentor for mentor in mentors}
    courses = []
    for name in COURSE_NAMES:
        mentor_email = next((email for email, names in MENTOR_COURSE_MAP.items() if name in names), None)
        mentor = mentor_map.get(mentor_email) if mentor_email else None
        courses.append(
            Course(
                name=name,
                code=name.upper().replace(" ", "-"),
                mentor_id=mentor.id if mentor else None,
                year=1,
                semester=1,
                max_hours=80,
            )
        )
    session.add_all(courses)
    await session.flush()
    return academic_year, semesters, groups, courses


async def link_profiles(session, students, parents, mentors, groups, academic_year):
    student_profiles = []
    parent_profiles = []
    mentor_profiles = []

    for student_index, student_user in enumerate(students):
        group = groups[student_index % len(groups)]
        student_profile = (await session.execute(select(StudentProfile).where(StudentProfile.user_id == student_user.id))).scalar_one()
        student_profile.current_group_id = group.id
        student_profile.admission_year = 2025
        student_profiles.append(student_profile)
        session.add(StudentGroupMembership(student_id=student_profile.id, group_id=group.id, academic_year_id=academic_year.id))

    for student_profile, parent_user in zip(student_profiles, parents, strict=False):
        parent_profile = (await session.execute(select(ParentProfile).where(ParentProfile.user_id == parent_user.id))).scalar_one()
        parent_profiles.append(parent_profile)
        session.add(StudentParentLink(student_id=student_profile.id, parent_id=parent_profile.id, is_active=True))

    for mentor_user, group in zip(mentors, groups * 2, strict=False):
        mentor_profile = (await session.execute(select(TutorProfile).where(TutorProfile.user_id == mentor_user.id))).scalar_one()
        mentor_profiles.append(mentor_profile)
        session.add(TutorGroupLink(tutor_id=mentor_profile.id, group_id=group.id, academic_year_id=academic_year.id))

    await session.commit()
    return student_profiles, parent_profiles, mentor_profiles


async def seed_activity(session, academic_year, semesters, groups, courses, mentors, students):
    current_semester = semesters[0]
    score_scope_year = academic_year.id

    for student_index, student_user in enumerate(students):
        student_profile = (await session.execute(select(StudentProfile).where(StudentProfile.user_id == student_user.id))).scalar_one()
        mentor_user = mentors[student_index % len(mentors)]
        mentor_profile = (await session.execute(select(TutorProfile).where(TutorProfile.user_id == mentor_user.id))).scalar_one()

        for course in courses:
            for day_offset in range(30):
                status = random.choices(
                    [AttendanceStatus.present, AttendanceStatus.late, AttendanceStatus.absent, AttendanceStatus.excused],
                    weights=[0.78, 0.1, 0.08, 0.04],
                )[0]
                session.add(
                    AttendanceRecord(
                        student_id=student_profile.id,
                        course_id=course.id,
                        semester_id=current_semester.id,
                        date=(datetime(2025, 9, 1) + timedelta(days=day_offset)).date().isoformat(),
                        status=status,
                        recorded_by_id=mentor_user.id,
                        note=None,
                    )
                )

            for assignment_index in range(1, 4):
                score = random.randint(62, 100)
                quality = random.choice(["excellent", "good", "satisfactory", "poor"])
                session.add(
                    GradeRecord(
                        student_id=student_profile.id,
                        course_id=course.id,
                        semester_id=current_semester.id,
                        assignment_name=f"{course.name} Assignment {assignment_index}",
                        score=score,
                        max_score=100,
                        submission_date=(datetime(2025, 9, 10) + timedelta(days=assignment_index)).date().isoformat(),
                        deadline=(datetime(2025, 9, 12) + timedelta(days=assignment_index)).date().isoformat(),
                        is_late=random.choice([False, False, True]),
                        quality=quality,
                        is_independent=random.choice([True, True, False]),
                        graded_by_id=mentor_user.id,
                    )
                )

        if student_index < 10:
            session.add(
                AchievementApplication(
                    student_id=student_profile.id,
                    semester_id=current_semester.id,
                    type=AchievementType.hackathon_participant,
                    title="Hackathon Participant",
                    description="Seeded demo achievement",
                    document_url=None,
                    points_claimed=1,
                    points_approved=1,
                    status=AchievementStatus.approved,
                    admin_note="Approved in seed",
                    reviewed_at=datetime.utcnow(),
                    reviewed_by_id=1,
                )
            )

        if student_index % 5 == 0:
            session.add(
                FeedbackEntry(
                    mentor_id=mentor_user.id,
                    student_id=student_profile.id,
                    semester_id=current_semester.id,
                    course_id=courses[0].id,
                    type=FeedbackType.academic,
                    content="Keep the pace, your recent work is improving.",
                    sentiment=None,
                    is_visible_to_student=True,
                )
            )

        session.add(
            TutorRating(
                mentor_id=mentor_user.id,
                student_id=student_profile.id,
                semester=current_semester.number,
                year=score_scope_year,
                corporate_culture=round(random.uniform(0.6, 1.0), 1),
                social_activity=round(random.uniform(0.6, 1.0), 1),
                soft_skills=round(random.uniform(0.6, 1.0), 1),
                discipline=round(random.uniform(0.6, 1.0), 1),
                dorm_activity=round(random.uniform(0.6, 1.0), 1),
                total=0.0,
                note="Seed tutor rating",
            )
        )

        session.add(
            DisciplineScore(
                student_id=student_profile.id,
                semester_id=current_semester.id,
                points=round(random.uniform(7.0, 10.0), 1),
                comment="Seed discipline score",
                updated_by_id=1,
            )
        )

        if student_index < 3:
            session.add(
                EmploymentRecord(
                    student_id=student_profile.id,
                    company_name=f"Demo Company {student_index + 1}",
                    position="Junior Intern",
                    type="internship",
                    hours_per_week=20,
                    start_date="2025-10-01",
                    end_date=None,
                    is_it_related=True,
                    bonus_points=round(random.uniform(3.0, 7.0), 1),
                    verified=True,
                    document_url=None,
                    semester_id=current_semester.id,
                    semester=current_semester.number,
                    year=2025,
                )
            )

        if student_index < 5:
            session.add(
                Penalty(
                    student_id=student_profile.id,
                    semester_id=current_semester.id,
                    amount=-random.choice([1, 3, 5]),
                    covered_amount=0,
                    comment="Seed penalty",
                    status=PenaltyStatus.active,
                    created_by_id=1,
                )
            )

        if student_index < 4:
            session.add(
                RecoveryTask(
                    student_id=student_profile.id,
                    assigned_by_id=1,
                    semester_id=current_semester.id,
                    semester=current_semester.number,
                    year=2025,
                    task_description="Support class cleanup and mentoring",
                    points_recoverable=2.0,
                    status="verified",
                    points_recovered=1.0,
                    due_date="2025-11-01",
                    completed_at=datetime.utcnow(),
                    verified_at=datetime.utcnow(),
                )
            )

        await calculate_student_score(session, student_profile.id, semester_id=current_semester.id, academic_year_id=academic_year.id, actor_id=1, reason="seed recalculation")

    await recalculate_rankings(session, semester_id=current_semester.id, academic_year_id=academic_year.id)
    await session.commit()


async def seed_demo_data() -> dict[str, int]:
    await reset_database()
    async with AsyncSessionLocal() as session:
        admin, mentors, students, parents = await create_users(session)
        academic_year, semesters, groups, courses = await create_academic_structure(session, mentors)
        await link_profiles(session, students, parents, mentors, groups, academic_year)
        await seed_activity(session, academic_year, semesters, groups, courses, mentors, students)
        await session.commit()

    return {
        "admin": 1,
        "mentors": len(mentors),
        "students": len(students),
        "parents": len(parents),
        "groups": len(groups),
        "courses": len(courses),
    }


async def main() -> None:
    summary = await seed_demo_data()
    print("Demo data seeded successfully.")
    print(f"Default demo password: {DEMO_PASSWORD}")
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
