from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Select, and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
	AcademicScore,
	AcademicYear,
	AchievementApplication,
	AchievementStatus,
	AttendanceRecord,
	AttendanceScore,
	Certificate,
	Course,
	DisciplineScore,
	EmploymentRecord,
	FeedbackEntry,
	GradeRecord,
	Notification,
	NotificationType,
	Penalty,
	PenaltyCoverage,
	Project,
	RecoveryTask,
	RankingSnapshot,
	ReviewStatus,
	ScoreHistoryLog,
	Semester,
	SentimentType,
	StudentProfile,
	TutorRating,
	TutorScore,
	User,
)


QUALITY_MULTIPLIERS = {
	None: 1.0,
	"excellent": 1.0,
	"good": 0.9,
	"satisfactory": 0.75,
	"poor": 0.5,
	"plagiarized": 0.0,
}


def clamp(value: float, minimum: float, maximum: float) -> float:
	return max(minimum, min(maximum, value))


async def get_current_semester(db: AsyncSession) -> Optional[Semester]:
	result = await db.execute(select(Semester).where(Semester.is_current.is_(True)).order_by(Semester.id.desc()))
	semester = result.scalar_one_or_none()
	if semester:
		return semester
	result = await db.execute(select(Semester).order_by(Semester.id.desc()))
	return result.scalars().first()


async def get_current_academic_year(db: AsyncSession) -> Optional[AcademicYear]:
	result = await db.execute(
		select(AcademicYear).where(AcademicYear.is_current.is_(True)).order_by(AcademicYear.id.desc())
	)
	academic_year = result.scalar_one_or_none()
	if academic_year:
		return academic_year
	result = await db.execute(select(AcademicYear).order_by(AcademicYear.id.desc()))
	return result.scalars().first()


async def _upsert_academic_score(
	db: AsyncSession,
	student_id: int,
	semester_id: int,
	average_gpa: float,
	percent: float,
	points: float,
) -> AcademicScore:
	result = await db.execute(
		select(AcademicScore).where(
			AcademicScore.student_id == student_id,
			AcademicScore.semester_id == semester_id,
		)
	)
	row = result.scalar_one_or_none()
	if row is None:
		row = AcademicScore(
			student_id=student_id,
			semester_id=semester_id,
			average_gpa=average_gpa,
			percent=percent,
			points=points,
		)
	else:
		row.average_gpa = average_gpa
		row.percent = percent
		row.points = points
	db.add(row)
	await db.flush()
	return row


async def _upsert_attendance_score(
	db: AsyncSession,
	student_id: int,
	semester_id: int,
	percent: float,
	points: float,
) -> AttendanceScore:
	result = await db.execute(
		select(AttendanceScore).where(
			AttendanceScore.student_id == student_id,
			AttendanceScore.semester_id == semester_id,
		)
	)
	row = result.scalar_one_or_none()
	if row is None:
		row = AttendanceScore(student_id=student_id, semester_id=semester_id, percent=percent, points=points)
	else:
		row.percent = percent
		row.points = points
	db.add(row)
	await db.flush()
	return row


async def _upsert_snapshot(
	db: AsyncSession,
	student_id: int,
	semester_id: int,
	academic_year_id: int,
	breakdown: dict[str, float],
	total_points: float,
	rank_position: int | None = None,
) -> RankingSnapshot:
	result = await db.execute(
		select(RankingSnapshot).where(
			RankingSnapshot.student_id == student_id,
			RankingSnapshot.semester_id == semester_id,
			RankingSnapshot.academic_year_id == academic_year_id,
		)
	)
	snapshot = result.scalar_one_or_none()
	if snapshot is None:
		snapshot = RankingSnapshot(
			student_id=student_id,
			semester_id=semester_id,
			academic_year_id=academic_year_id,
		)
	snapshot.academic_points = breakdown["academic"]
	snapshot.attendance_points = breakdown["attendance"]
	snapshot.certificate_points = breakdown["activity"]
	snapshot.project_points = breakdown["practical"]
	snapshot.discipline_points = breakdown["discipline"]
	snapshot.tutor_points = breakdown["tutor"]
	snapshot.work_points = breakdown["employment"]
	snapshot.penalty_points = breakdown["penalty"] + breakdown["recovery"]
	snapshot.total_points = total_points
	snapshot.rank_position = rank_position
	snapshot.calculated_at = datetime.utcnow()
	db.add(snapshot)
	await db.flush()
	return snapshot


async def _log_history(
	db: AsyncSession,
	student_id: int,
	field_name: str,
	old_value: Any,
	new_value: Any,
	reason: str | None,
	actor_id: int | None,
) -> None:
	db.add(
		ScoreHistoryLog(
			student_id=student_id,
			actor_id=actor_id,
			field_name=field_name,
			old_value=None if old_value is None else str(old_value),
			new_value=None if new_value is None else str(new_value),
			reason=reason,
		)
	)


async def calculate_student_score(
	db: AsyncSession,
	student_id: int,
	semester_id: int | None = None,
	academic_year_id: int | None = None,
	actor_id: int | None = None,
	reason: str | None = None,
) -> dict[str, Any]:
	semester = None
	academic_year = None
	if semester_id is None:
		semester = await get_current_semester(db)
		if semester is None:
			raise ValueError("No semester available")
		semester_id = semester.id
	else:
		result = await db.execute(select(Semester).where(Semester.id == semester_id))
		semester = result.scalar_one_or_none()
	if academic_year_id is None:
		if semester is None:
			semester = await get_current_semester(db)
		if semester is None:
			raise ValueError("No academic year available")
		academic_year_id = semester.academic_year_id
		result = await db.execute(select(AcademicYear).where(AcademicYear.id == academic_year_id))
		academic_year = result.scalar_one_or_none()
	else:
		result = await db.execute(select(AcademicYear).where(AcademicYear.id == academic_year_id))
		academic_year = result.scalar_one_or_none()

	if semester is None:
		result = await db.execute(select(Semester).where(Semester.id == semester_id))
		semester = result.scalar_one_or_none()
	if semester is None or academic_year is None:
		raise ValueError("Unable to resolve current score scope")

	grade_result = await db.execute(
		select(GradeRecord.score, GradeRecord.max_score, GradeRecord.is_late, GradeRecord.is_independent, GradeRecord.quality)
		.where(GradeRecord.student_id == student_id, GradeRecord.semester_id == semester_id)
	)
	grades = grade_result.all()
	grade_percentages: list[float] = []
	practical_scores: list[float] = []
	for score, max_score, is_late, is_independent, quality in grades:
		max_score = max_score or 100.0
		if max_score <= 0:
			continue
		percentage = (float(score) / float(max_score)) * 100.0
		if is_late:
			percentage *= 0.8
		if not is_independent:
			percentage = 0.0
		multiplier = QUALITY_MULTIPLIERS.get(quality, 1.0)
		percentage *= multiplier
		grade_percentages.append(clamp(percentage, 0.0, 100.0))
		practical_scores.append(clamp(percentage, 0.0, 100.0))

	academic_percentage = sum(grade_percentages) / len(grade_percentages) if grade_percentages else 0.0
	academic_points = clamp((academic_percentage / 100.0) * 40.0, 0.0, 40.0)
	practical_average = sum(practical_scores) / len(practical_scores) if practical_scores else 0.0
	practical_points = clamp((practical_average / 100.0) * 15.0, 0.0, 15.0)

	attendance_result = await db.execute(
		select(AttendanceRecord.status).where(
			AttendanceRecord.student_id == student_id,
			AttendanceRecord.semester_id == semester_id,
		)
	)
	attendance_rows = [row[0] for row in attendance_result.all()]
	attendance_total = len(attendance_rows)
	attendance_present = sum(1 for status in attendance_rows if getattr(status, "value", status) == "present")
	attendance_late = sum(1 for status in attendance_rows if getattr(status, "value", status) == "late")
	attendance_marked = attendance_present + attendance_late
	attendance_percent = (attendance_marked / attendance_total * 100.0) if attendance_total else 0.0
	attendance_points = clamp((attendance_percent / 100.0) * 20.0, 0.0, 20.0)

	achievement_result = await db.execute(
		select(func.coalesce(func.sum(AchievementApplication.points_approved), 0.0)).where(
			AchievementApplication.student_id == student_id,
			AchievementApplication.semester_id == semester_id,
			AchievementApplication.status == AchievementStatus.approved,
		)
	)
	achievement_points = float(achievement_result.scalar_one() or 0.0)
	certificate_result = await db.execute(
		select(func.coalesce(func.sum(Certificate.points), 0.0)).where(
			Certificate.student_id == student_id,
			Certificate.semester_id == semester_id,
			Certificate.status == ReviewStatus.approved,
		)
	)
	project_result = await db.execute(
		select(func.coalesce(func.sum(Project.points), 0.0)).where(
			Project.student_id == student_id,
			Project.semester_id == semester_id,
			Project.status == ReviewStatus.approved,
		)
	)
	activity_points = clamp(achievement_points + float(certificate_result.scalar_one() or 0.0) + float(project_result.scalar_one() or 0.0), 0.0, 10.0)

	tutor_result = await db.execute(
		select(func.coalesce(func.avg(TutorRating.total), 0.0)).where(
			TutorRating.student_id == student_id,
			TutorRating.semester == semester.number,
			TutorRating.year == academic_year.id,
		)
	)
	tutor_points = clamp(float(tutor_result.scalar_one() or 0.0), 0.0, 5.0)

	discipline_result = await db.execute(
		select(DisciplineScore.points).where(
			DisciplineScore.student_id == student_id,
			DisciplineScore.semester_id == semester_id,
		).order_by(DisciplineScore.updated_at.desc())
	)
	discipline_points = 10.0
	latest_discipline = discipline_result.scalars().first()
	if latest_discipline is not None:
		discipline_points = clamp(float(latest_discipline), 0.0, 10.0)

	penalty_result = await db.execute(
		select(func.coalesce(func.sum(Penalty.amount), 0)).where(
			Penalty.student_id == student_id,
			Penalty.semester_id == semester_id,
		)
	)
	penalty_points = float(penalty_result.scalar_one() or 0.0)
	penalty_points = clamp(penalty_points, -20.0, 0.0)

	recovery_result = await db.execute(
		select(func.coalesce(func.sum(RecoveryTask.points_recovered), 0.0)).where(
			RecoveryTask.student_id == student_id,
			RecoveryTask.semester_id == semester_id,
			RecoveryTask.status == "verified",
		)
	)
	recovery_points = clamp(float(recovery_result.scalar_one() or 0.0), 0.0, 10.0)

	employment_result = await db.execute(
		select(func.coalesce(func.sum(EmploymentRecord.bonus_points), 0.0)).where(
			EmploymentRecord.student_id == student_id,
			EmploymentRecord.semester_id == semester_id,
			EmploymentRecord.verified.is_(True),
		)
	)
	employment_points = clamp(float(employment_result.scalar_one() or 0.0), 0.0, 10.0)

	base_total = academic_points + attendance_points + practical_points + activity_points + tutor_points + discipline_points
	final_score = clamp(base_total + penalty_points + recovery_points + employment_points, 0.0, 120.0)
	grant_eligible = final_score >= 80.0 and academic_percentage >= 80.0

	breakdown = {
		"academic": academic_points,
		"attendance": attendance_points,
		"practical": practical_points,
		"activity": activity_points,
		"tutor": tutor_points,
		"discipline": discipline_points,
		"penalty": penalty_points,
		"recovery": recovery_points,
		"employment": employment_points,
	}

	snapshot = await _upsert_snapshot(
		db=db,
		student_id=student_id,
		semester_id=semester_id,
		academic_year_id=academic_year_id,
		breakdown=breakdown,
		total_points=final_score,
	)

	await _upsert_academic_score(db, student_id, semester_id, academic_percentage, academic_percentage, academic_points)
	await _upsert_attendance_score(db, student_id, semester_id, attendance_percent, attendance_points)

	await _log_history(db, student_id, "academic_points", None, academic_points, reason, actor_id)
	await _log_history(db, student_id, "attendance_points", None, attendance_points, reason, actor_id)
	await _log_history(db, student_id, "practical_points", None, practical_points, reason, actor_id)
	await _log_history(db, student_id, "activity_points", None, activity_points, reason, actor_id)
	await _log_history(db, student_id, "tutor_points", None, tutor_points, reason, actor_id)
	await _log_history(db, student_id, "discipline_points", None, discipline_points, reason, actor_id)
	await _log_history(db, student_id, "penalty_points", None, penalty_points, reason, actor_id)
	await _log_history(db, student_id, "recovery_points", None, recovery_points, reason, actor_id)
	await _log_history(db, student_id, "employment_points", None, employment_points, reason, actor_id)

	await db.commit()

	return {
		"student_id": student_id,
		"semester_id": semester_id,
		"academic_year_id": academic_year_id,
		"academic_score": academic_points,
		"academic_percentage": academic_percentage,
		"attendance_score": attendance_points,
		"attendance_percentage": attendance_percent,
		"practical_score": practical_points,
		"activity_score": activity_points,
		"tutor_score": tutor_points,
		"discipline_score": discipline_points,
		"penalty_points": penalty_points,
		"recovery_points": recovery_points,
		"employment_bonus": employment_points,
		"base_total": base_total,
		"final_score": final_score,
		"grant_eligible": grant_eligible,
		"snapshot_id": snapshot.id,
	}


async def recalculate_rankings(
	db: AsyncSession,
	semester_id: int,
	academic_year_id: int,
) -> list[RankingSnapshot]:
	result = await db.execute(
		select(RankingSnapshot)
		.where(RankingSnapshot.semester_id == semester_id, RankingSnapshot.academic_year_id == academic_year_id)
		.order_by(
			RankingSnapshot.total_points.desc(),
			RankingSnapshot.work_points.desc(),
			RankingSnapshot.academic_points.desc(),
			RankingSnapshot.attendance_points.desc(),
		)
	)
	snapshots = list(result.scalars().all())
	for index, snapshot in enumerate(snapshots, start=1):
		snapshot.rank_position = index
	await db.commit()
	return snapshots


async def get_year_leaderboard(db: AsyncSession, academic_year_id: int) -> list[dict[str, Any]]:
	result = await db.execute(
		select(
			RankingSnapshot.student_id,
			StudentProfile.student_code,
			func.sum(RankingSnapshot.total_points).label("total_points"),
			func.sum(RankingSnapshot.academic_points).label("academic_points"),
			func.sum(RankingSnapshot.attendance_points).label("attendance_points"),
			func.sum(RankingSnapshot.project_points).label("project_points"),
			func.sum(RankingSnapshot.certificate_points).label("certificate_points"),
			func.sum(RankingSnapshot.discipline_points).label("discipline_points"),
			func.sum(RankingSnapshot.tutor_points).label("tutor_points"),
			func.sum(RankingSnapshot.work_points).label("work_points"),
			func.sum(RankingSnapshot.penalty_points).label("penalty_points"),
		)
		.join(StudentProfile, StudentProfile.id == RankingSnapshot.student_id)
		.where(RankingSnapshot.academic_year_id == academic_year_id)
		.group_by(RankingSnapshot.student_id, StudentProfile.student_code)
		.order_by(
			func.sum(RankingSnapshot.total_points).desc(),
			func.sum(RankingSnapshot.work_points).desc(),
			func.sum(RankingSnapshot.academic_points).desc(),
		)
	)
	rows = result.all()
	leaderboard: list[dict[str, Any]] = []
	for index, row in enumerate(rows, start=1):
		leaderboard.append(
			{
				"rank": index,
				"student_id": row.student_id,
				"student_code": row.student_code,
				"total_points": float(row.total_points or 0.0),
				"academic_points": float(row.academic_points or 0.0),
				"attendance_points": float(row.attendance_points or 0.0),
				"project_points": float(row.project_points or 0.0),
				"certificate_points": float(row.certificate_points or 0.0),
				"discipline_points": float(row.discipline_points or 0.0),
				"tutor_points": float(row.tutor_points or 0.0),
				"work_points": float(row.work_points or 0.0),
				"penalty_points": float(row.penalty_points or 0.0),
			}
		)
	return leaderboard

