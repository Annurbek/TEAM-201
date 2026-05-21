"""Demo data seeder — populates ALL models for testing.

Usage:
    python -m app.db.seed
    python scripts/seed_demo_data.py

Default password for all users: DemoPass123!
"""

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
    AcademicScore,
    AcademicYear,
    AchievementApplication,
    AchievementStatus,
    AchievementType,
    AttendanceRecord,
    AttendanceScore,
    AttendanceStatus,
    AuditAction,
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
    NotificationType,
    ParentProfile,
    Penalty,
    PenaltyCoverage,
    PenaltyStatus,
    Project,
    RankingSnapshot,
    RecoveryTask,
    ReviewStatus,
    ScoreHistoryLog,
    Semester,
    SentimentType,
    StudentGroupMembership,
    StudentParentLink,
    StudentProfile,
    TutorGroupLink,
    TutorProfile,
    TutorRating,
    TutorScore,
    User,
    UserRole,
    WorkScore,
    WorkType,
)
from app.models.edumetric import Notification as NotificationModel
from app.services.auth_service import AuthService
from app.services.score_service import calculate_student_score, recalculate_rankings

# ─── Constants ────────────────────────────────────────────────────────────────

ADMIN_EMAIL = "admin@pdp.uz"
MENTOR_EMAILS = ["mentor1@pdp.uz", "mentor2@pdp.uz", "mentor3@pdp.uz"]
STUDENT_COUNT = 20
PARENT_COUNT = 10  # not all students have parents linked
DEMO_PASSWORD = "DemoPass123!"

COURSE_NAMES = ["ITS", "Programming", "Website", "Full Stack", "BPM", "Big Data"]
MENTOR_COURSE_MAP = {
    "mentor1@pdp.uz": ["Programming", "Full Stack"],
    "mentor2@pdp.uz": ["ITS", "BPM"],
    "mentor3@pdp.uz": ["Website", "Big Data"],
}

ACHIEVEMENT_TYPES = [
    (AchievementType.hackathon_participant, "Hackathon Participant", 1),
    (AchievementType.hackathon_winner, "Hackathon Winner", 3),
    (AchievementType.startup, "Startup Project", 7),
    (AchievementType.mentoring, "Mentoring Session", 3),
    (AchievementType.certificate_online, "Online Certificate", 2),
    (AchievementType.certificate_offline, "Offline Certificate", 3),
    (AchievementType.certificate_national_it, "National IT Certificate", 2),
    (AchievementType.certificate_language, "Language Certificate", 5),
    (AchievementType.certificate_international, "International Certificate", 10),
    (AchievementType.volunteering, "Volunteering", 2),
    (AchievementType.soft_skills, "Soft Skills Workshop", 1),
    (AchievementType.networking, "Networking Event", 1),
    (AchievementType.project_participant, "Project Participant", 2),
    (AchievementType.direction_assistant, "Direction Assistant", 3),
    (AchievementType.strategic_assistant, "Strategic Assistant", 4),
]

COMPANY_NAMES = [
    "Uzum Tech", "PDP Academy", "EPAM Systems", "Inha University",
    "Tech Corp", "Digital Solutions", "IT Park", "Smart Brain",
]

FEEDBACK_TEMPLATES = [
    ("academic", "Great progress in coursework. Keep it up!", SentimentType.positive),
    ("academic", "Needs to improve assignment submission timeliness.", SentimentType.neutral),
    ("behavioral", "Excellent teamwork during group projects.", SentimentType.positive),
    ("behavioral", "Should participate more actively in class discussions.", SentimentType.neutral),
    ("project", "Project implementation shows strong technical skills.", SentimentType.positive),
    ("general", "Overall performance is satisfactory. Room for growth.", SentimentType.neutral),
    ("academic", "Outstanding exam results this semester.", SentimentType.positive),
    ("project", "Code quality needs improvement. Review best practices.", SentimentType.negative),
]

PENALTY_TYPES = [
    ("Late submission", "Assignment submitted past deadline"),
    ("Absence", "Unexcused absence from class"),
    ("Plagiarism", "Code similarity detected"),
    ("Disruption", "Disruptive behavior during lecture"),
    ("Dress code", "Violation of dress code policy"),
]

# ─── Database reset ───────────────────────────────────────────────────────────


async def reset_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)


# ─── Users ────────────────────────────────────────────────────────────────────


async def create_users(session) -> tuple[User, list[User], list[User], list[User]]:
    admin = await AuthService.register_user(
        session, full_name="PDP Admin", username=ADMIN_EMAIL,
        password=DEMO_PASSWORD, role=UserRole.admin, phone="+998901111111",
    )

    mentors = []
    for full_name, username in [("Mentor One", "mentor1@pdp.uz"), ("Mentor Two", "mentor2@pdp.uz"), ("Mentor Three", "mentor3@pdp.uz")]:
        mentors.append(await AuthService.register_user(
            session, full_name=full_name, username=username,
            password=DEMO_PASSWORD, role=UserRole.tutor,
            phone=f"+99890{random.randint(1000000, 9999999)}",
        ))

    students = []
    for i in range(1, STUDENT_COUNT + 1):
        students.append(await AuthService.register_user(
            session, full_name=f"Student {i:02d}", username=f"student{i:02d}@pdp.uz",
            password=DEMO_PASSWORD, role=UserRole.student,
            phone=f"+99891{i:07d}", student_code=f"PDP-2025-{i:03d}",
        ))

    parents = []
    for i in range(1, PARENT_COUNT + 1):
        parents.append(await AuthService.register_user(
            session, full_name=f"Parent {i:02d}", username=f"parent{i:02d}@pdp.uz",
            password=DEMO_PASSWORD, role=UserRole.parent,
            phone=f"+99893{i:07d}",
        ))

    await session.commit()
    return admin, mentors, students, parents


# ─── Academic structure ───────────────────────────────────────────────────────


async def create_academic_structure(session, mentors):
    academic_year = AcademicYear(
        name="2025-2026", start_date=datetime(2025, 9, 1),
        end_date=datetime(2026, 6, 30), is_current=True,
    )
    session.add(academic_year)
    await session.flush()

    semesters = [
        Semester(academic_year_id=academic_year.id, number=1,
                 start_date=datetime(2025, 9, 1), end_date=datetime(2026, 1, 31), is_current=True),
        Semester(academic_year_id=academic_year.id, number=2,
                 start_date=datetime(2026, 2, 1), end_date=datetime(2026, 6, 30), is_current=False),
    ]
    session.add_all(semesters)
    await session.flush()

    groups = [
        Group(name="CS-101", course=1, academic_year_id=academic_year.id),
        Group(name="CS-102", course=2, academic_year_id=academic_year.id),
    ]
    session.add_all(groups)
    await session.flush()

    mentor_map = {m.username: m for m in mentors}
    courses = []
    for name in COURSE_NAMES:
        mentor_email = next((e for e, names in MENTOR_COURSE_MAP.items() if name in names), None)
        mentor = mentor_map.get(mentor_email) if mentor_email else None
        courses.append(Course(
            name=name, code=name.upper().replace(" ", "-"),
            mentor_id=mentor.id if mentor else None, year=1, semester=1, max_hours=80,
        ))
    session.add_all(courses)
    await session.flush()

    return academic_year, semesters, groups, courses


# ─── Profile linking ──────────────────────────────────────────────────────────


async def link_profiles(session, students, parents, mentors, groups, academic_year):
    student_profiles = []
    parent_profiles = []

    for i, student_user in enumerate(students):
        group = groups[i % len(groups)]
        sp = (await session.execute(select(StudentProfile).where(StudentProfile.user_id == student_user.id))).scalar_one()
        sp.current_group_id = group.id
        sp.admission_year = 2025
        student_profiles.append(sp)
        session.add(StudentGroupMembership(student_id=sp.id, group_id=group.id, academic_year_id=academic_year.id))

    for sp, parent_user in zip(student_profiles[:PARENT_COUNT], parents):
        pp = (await session.execute(select(ParentProfile).where(ParentProfile.user_id == parent_user.id))).scalar_one()
        parent_profiles.append(pp)
        session.add(StudentParentLink(student_id=sp.id, parent_id=pp.id, is_active=True))

    for mentor_user, group in zip(mentors, groups * 2):
        mp = (await session.execute(select(TutorProfile).where(TutorProfile.user_id == mentor_user.id))).scalar_one()
        session.add(TutorGroupLink(tutor_id=mp.id, group_id=group.id, academic_year_id=academic_year.id))

    await session.commit()
    return student_profiles, parent_profiles


# ─── Activity seeding ─────────────────────────────────────────────────────────


async def seed_activity(session, academic_year, semesters, groups, courses, mentors, students, admin):
    current_semester = semesters[0]
    year_id = academic_year.id

    for si, student_user in enumerate(students):
        sp = (await session.execute(select(StudentProfile).where(StudentProfile.user_id == student_user.id))).scalar_one()
        mentor = mentors[si % len(mentors)]
        mp = (await session.execute(select(TutorProfile).where(TutorProfile.user_id == mentor.id))).scalar_one()

        # ── Attendance (30 days × 6 courses = 180 records per student) ──
        for course in courses:
            for day in range(30):
                status = random.choices(
                    [AttendanceStatus.present, AttendanceStatus.late, AttendanceStatus.absent, AttendanceStatus.excused],
                    weights=[0.78, 0.1, 0.08, 0.04],
                )[0]
                session.add(AttendanceRecord(
                    student_id=sp.id, course_id=course.id, semester_id=current_semester.id,
                    date=(datetime(2025, 9, 1) + timedelta(days=day)).date().isoformat(),
                    status=status, recorded_by_id=mentor.id,
                ))

        # ── Grades (3 assignments × 6 courses = 18 per student) ──
        for course in courses:
            for ai in range(1, 4):
                score = random.randint(62, 100)
                session.add(GradeRecord(
                    student_id=sp.id, course_id=course.id, semester_id=current_semester.id,
                    assignment_name=f"{course.name} Assignment {ai}",
                    score=score, max_score=100,
                    submission_date=(datetime(2025, 9, 10) + timedelta(days=ai)).date().isoformat(),
                    deadline=(datetime(2025, 9, 12) + timedelta(days=ai)).date().isoformat(),
                    is_late=random.choice([False, False, True]),
                    quality=random.choice(["excellent", "good", "satisfactory", "poor"]),
                    is_independent=random.choice([True, True, False]),
                    graded_by_id=mentor.id,
                ))

        # ── Achievements (varied types) ──
        if si < 15:
            num_achievements = random.randint(1, 4)
            chosen = random.sample(ACHIEVEMENT_TYPES, min(num_achievements, len(ACHIEVEMENT_TYPES)))
            for atype, title, pts in chosen:
                approved = si < 10
                session.add(AchievementApplication(
                    student_id=sp.id, semester_id=current_semester.id,
                    type=atype, title=title, description=f"Demo: {title}",
                    document_url=None, points_claimed=pts,
                    points_approved=pts if approved else None,
                    status=AchievementStatus.approved if approved else AchievementStatus.pending,
                    admin_note="Approved in seed" if approved else None,
                    reviewed_at=datetime.utcnow() if approved else None,
                    reviewed_by_id=admin.id if approved else None,
                ))

        # ── Certificates ──
        if si < 8:
            session.add(Certificate(
                student_id=sp.id, semester_id=current_semester.id,
                title=f"Python Mastery Certificate", file_url="/uploads/certs/cert_{si}.pdf",
                points=round(random.uniform(1.0, 3.0), 1),
                status=ReviewStatus.approved, reviewed_by_id=admin.id,
                reviewed_at=datetime.utcnow(),
            ))

        # ── Projects ──
        if si < 6:
            session.add(Project(
                student_id=sp.id, semester_id=current_semester.id,
                title=f"E-Commerce Platform", description="Full-stack web application",
                file_url="/uploads/projects/proj_{si}.zip",
                points=round(random.uniform(2.0, 5.0), 1),
                status=ReviewStatus.approved, reviewed_by_id=admin.id,
                reviewed_at=datetime.utcnow(),
            ))

        # ── Feedback ──
        if si % 3 == 0:
            ftype, content, sentiment = random.choice(FEEDBACK_TEMPLATES)
            session.add(FeedbackEntry(
                mentor_id=mentor.id, student_id=sp.id,
                semester_id=current_semester.id, course_id=courses[si % len(courses)].id,
                type=FeedbackType(ftype), content=content,
                sentiment=sentiment, is_visible_to_student=True,
            ))

        # ── Tutor Rating ──
        total = round(random.uniform(3.0, 5.0), 1)
        session.add(TutorRating(
            mentor_id=mentor.id, student_id=sp.id,
            semester=current_semester.number, year=year_id,
            corporate_culture=round(random.uniform(0.6, 1.0), 1),
            social_activity=round(random.uniform(0.6, 1.0), 1),
            soft_skills=round(random.uniform(0.6, 1.0), 1),
            discipline=round(random.uniform(0.6, 1.0), 1),
            dorm_activity=round(random.uniform(0.6, 1.0), 1),
            total=total, note="Seed rating",
        ))

        # ── TutorScore ──
        session.add(TutorScore(
            student_id=sp.id, tutor_id=mp.id, semester_id=current_semester.id,
            points=total, comment="Seed tutor score",
        ))

        # ── DisciplineScore ──
        session.add(DisciplineScore(
            student_id=sp.id, semester_id=current_semester.id,
            points=round(random.uniform(7.0, 10.0), 1),
            comment="Seed discipline", updated_by_id=admin.id,
        ))

        # ── WorkScore ──
        if si < 5:
            session.add(WorkScore(
                student_id=sp.id, semester_id=current_semester.id,
                work_type=random.choice([WorkType.freelance, WorkType.part_time, WorkType.full_time]),
                points=round(random.uniform(3.0, 8.0), 1),
                updated_by_id=admin.id,
            ))

        # ── Employment ──
        if si < 5:
            session.add(EmploymentRecord(
                student_id=sp.id, company_name=random.choice(COMPANY_NAMES),
                position=random.choice(["Junior Developer", "Intern", "QA Engineer"]),
                type=random.choice(["freelance", "part_time", "full_time"]),
                hours_per_week=random.choice([10, 20, 40]),
                start_date="2025-10-01", end_date=None,
                is_it_related=True,
                bonus_points=round(random.uniform(3.0, 7.0), 1),
                verified=si < 3, document_url=None,
                semester_id=current_semester.id, semester=current_semester.number, year=2025,
            ))

        # ── Penalty + PenaltyCoverage ──
        if si < 8:
            ptype, preason = random.choice(PENALTY_TYPES)
            amount = -random.choice([1, 3, 5])
            penalty = Penalty(
                student_id=sp.id, semester_id=current_semester.id,
                amount=amount, covered_amount=0,
                comment=f"{ptype}: {preason}",
                status=PenaltyStatus.active, created_by_id=admin.id,
            )
            session.add(penalty)
            await session.flush()

            # PenaltyCoverage for some penalties
            if si < 3:
                coverage_amount = min(abs(amount), random.randint(1, 3))
                session.add(PenaltyCoverage(
                    penalty_id=penalty.id, covered_by_id=admin.id,
                    amount=coverage_amount,
                ))
                penalty.covered_amount = coverage_amount

        # ── RecoveryTask ──
        if si < 6:
            statuses = ["pending", "completed", "verified"]
            rstatus = statuses[min(si, 2)]
            session.add(RecoveryTask(
                student_id=sp.id, assigned_by_id=admin.id,
                semester_id=current_semester.id,
                semester=current_semester.number, year=2025,
                task_description="Support class cleanup and mentoring",
                points_recoverable=round(random.uniform(1.0, 5.0), 1),
                status=rstatus,
                points_recovered=round(random.uniform(1.0, 3.0), 1) if rstatus == "verified" else 0.0,
                due_date="2025-11-01",
                completed_at=datetime.utcnow() if rstatus in ("completed", "verified") else None,
                verified_at=datetime.utcnow() if rstatus == "verified" else None,
            ))

        # ── Notifications ──
        session.add(NotificationModel(
            user_id=student_user.id, title="Welcome to PDP",
            message="Your account has been created. Login to get started.",
            type=NotificationType.info, is_read=si < 5,
        ))

        # ── Calculate score (creates AcademicScore, AttendanceScore, RankingSnapshot, ScoreHistoryLog, AuditLog) ──
        await calculate_student_score(
            session, sp.id, semester_id=current_semester.id,
            academic_year_id=academic_year.id, actor_id=admin.id,
            reason="seed recalculation",
        )

    await recalculate_rankings(session, semester_id=current_semester.id, academic_year_id=academic_year.id)

    # ── Extra notifications for admin ──
    session.add(NotificationModel(
        user_id=admin.id, title="System Ready",
        message="Demo data has been seeded successfully.",
        type=NotificationType.success, is_read=False,
    ))

    await session.commit()


# ─── Main ─────────────────────────────────────────────────────────────────────


async def seed_demo_data() -> dict[str, int]:
    await reset_database()
    async with AsyncSessionLocal() as session:
        admin, mentors, students, parents = await create_users(session)
        academic_year, semesters, groups, courses = await create_academic_structure(session, mentors)
        student_profiles, parent_profiles = await link_profiles(session, students, parents, mentors, groups, academic_year)
        await seed_activity(session, academic_year, semesters, groups, courses, mentors, students, admin)

    return {
        "users": 1 + len(mentors) + len(students) + len(parents),
        "admin": 1,
        "mentors": len(mentors),
        "students": len(students),
        "parents": len(parents),
        "groups": len(groups),
        "courses": len(courses),
        "semesters": len(semesters),
        "attendance_records": len(students) * len(courses) * 30,
        "grade_records": len(students) * len(courses) * 3,
    }


async def main() -> None:
    print("Seeding demo data...")
    summary = await seed_demo_data()
    print("\n[OK] Demo data seeded successfully!")
    print(f"\nDefault password: {DEMO_PASSWORD}")
    print("\nSummary:")
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print("\nLogin credentials:")
    print(f"   Admin:   {ADMIN_EMAIL} / {DEMO_PASSWORD}")
    for i, email in enumerate(MENTOR_EMAILS, 1):
        print(f"   Mentor {i}: {email} / {DEMO_PASSWORD}")
    print(f"   Students: student01@pdp.uz ... student{STUDENT_COUNT:02d}@pdp.uz / {DEMO_PASSWORD}")
    print(f"   Parents:  parent01@pdp.uz ... parent{PARENT_COUNT:02d}@pdp.uz / {DEMO_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
