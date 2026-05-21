"""Permission definitions for the RBAC/ABAC system.

Structure: {resource}.{action}

Resources:
    user          — управление пользователями
    student       — данные студентов
    group         — группы
    course        — курсы
    attendance    — посещаемость
    grade         — оценки
    achievement   — достижения
    feedback      — фидбек
    penalty       — штрафы
    recovery      — восстановление баллов
    employment    — трудоустройство
    score_history — история изменения баллов
    ranking       — рейтинги
    audit_log     — лог аудита
    notification  — уведомления
    report        — отчёты
    config        — конфигурация системы

Actions:
    view    — просмотр
    create  — создание
    edit    — редактирование
    delete  — удаление
    manage  — полный CRUD + специальные операции
    approve — подтверждение/отклонение
    export  — экспорт данных
    recalculate — перерасчёт
"""

from __future__ import annotations

from enum import Enum


class Permission(str, Enum):
    # ─── Users ─────────────────────────────────────────────
    user_view = "user.view"
    user_create = "user.create"
    user_edit = "user.edit"
    user_delete = "user.delete"
    user_manage = "user.manage"
    user_toggle_active = "user.toggle_active"

    # ─── Students ──────────────────────────────────────────
    student_view = "student.view"
    student_view_own = "student.view.own"
    student_view_children = "student.view.children"
    student_view_group = "student.view.group"
    student_manage = "student.manage"
    student_export = "student.export"

    # ─── Groups ────────────────────────────────────────────
    group_view = "group.view"
    group_create = "group.create"
    group_edit = "group.edit"
    group_delete = "group.delete"
    group_manage = "group.manage"

    # ─── Courses ───────────────────────────────────────────
    course_view = "course.view"
    course_create = "course.create"
    course_edit = "course.edit"
    course_delete = "course.delete"
    course_manage = "course.manage"

    # ─── Attendance ────────────────────────────────────────
    attendance_view = "attendance.view"
    attendance_view_own = "attendance.view.own"
    attendance_view_children = "attendance.view.children"
    attendance_create = "attendance.create"
    attendance_edit = "attendance.edit"
    attendance_delete = "attendance.delete"
    attendance_manage = "attendance.manage"

    # ─── Grades ────────────────────────────────────────────
    grade_view = "grade.view"
    grade_view_own = "grade.view.own"
    grade_view_children = "grade.view.children"
    grade_create = "grade.create"
    grade_edit = "grade.edit"
    grade_delete = "grade.delete"
    grade_manage = "grade.manage"

    # ─── Achievements ──────────────────────────────────────
    achievement_view = "achievement.view"
    achievement_view_own = "achievement.view.own"
    achievement_create = "achievement.create"
    achievement_approve = "achievement.approve"
    achievement_reject = "achievement.reject"
    achievement_delete = "achievement.delete"
    achievement_manage = "achievement.manage"

    # ─── Feedback ──────────────────────────────────────────
    feedback_view = "feedback.view"
    feedback_view_own = "feedback.view.own"
    feedback_view_children = "feedback.view.children"
    feedback_create = "feedback.create"
    feedback_edit = "feedback.edit"
    feedback_delete = "feedback.delete"
    feedback_manage = "feedback.manage"

    # ─── Penalties ─────────────────────────────────────────
    penalty_view = "penalty.view"
    penalty_view_own = "penalty.view.own"
    penalty_view_children = "penalty.view.children"
    penalty_create = "penalty.create"
    penalty_edit = "penalty.edit"
    penalty_manage = "penalty.manage"

    # ─── Recovery ──────────────────────────────────────────
    recovery_view = "recovery.view"
    recovery_view_own = "recovery.view.own"
    recovery_view_children = "recovery.view.children"
    recovery_create = "recovery.create"
    recovery_verify = "recovery.verify"
    recovery_manage = "recovery.manage"

    # ─── Employment ────────────────────────────────────────
    employment_view = "employment.view"
    employment_view_own = "employment.view.own"
    employment_create = "employment.create"
    employment_verify = "employment.verify"
    employment_manage = "employment.manage"

    # ─── Score History ─────────────────────────────────────
    score_history_view = "score_history.view"
    score_history_view_own = "score_history.view.own"
    score_history_view_children = "score_history.view.children"
    score_history_edit = "score_history.edit"
    score_history_recalculate = "score_history.recalculate"
    score_history_manage = "score_history.manage"

    # ─── Rankings ──────────────────────────────────────────
    ranking_view = "ranking.view"
    ranking_view_own = "ranking.view.own"
    ranking_view_children = "ranking.view.children"
    ranking_recalculate = "ranking.recalculate"
    ranking_manage = "ranking.manage"

    # ─── Audit Log ─────────────────────────────────────────
    audit_log_view = "audit_log.view"
    audit_log_manage = "audit_log.manage"

    # ─── Notifications ─────────────────────────────────────
    notification_view = "notification.view"
    notification_view_own = "notification.view.own"
    notification_send = "notification.send"
    notification_manage = "notification.manage"

    # ─── Reports ───────────────────────────────────────────
    report_view = "report.view"
    report_grant = "report.grant"
    report_export = "report.export"
    report_manage = "report.manage"

    # ─── Config / System ───────────────────────────────────
    config_view = "config.view"
    config_edit = "config.edit"
    config_manage = "config.manage"
    academic_year_manage = "academic_year.manage"
    semester_manage = "semester.manage"
    dashboard_view = "dashboard.view"


# ─── Permission sets by role ───────────────────────────────
# These define the DEFAULT permissions for each role.
# Individual users can have additional permissions assigned.

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "super_admin": frozenset({p.value for p in Permission}),

    "admin": frozenset({
        # Users
        Permission.user_view,
        Permission.user_create,
        Permission.user_edit,
        Permission.user_toggle_active,
        # Students
        Permission.student_manage,
        Permission.student_export,
        # Groups
        Permission.group_manage,
        # Courses
        Permission.course_manage,
        # Attendance
        Permission.attendance_manage,
        # Grades
        Permission.grade_manage,
        # Achievements
        Permission.achievement_manage,
        # Feedback
        Permission.feedback_manage,
        # Penalties
        Permission.penalty_manage,
        # Recovery
        Permission.recovery_manage,
        # Employment
        Permission.employment_manage,
        # Score history
        Permission.score_history_view,
        Permission.score_history_edit,
        Permission.score_history_recalculate,
        Permission.score_history_manage,
        # Rankings
        Permission.ranking_view,
        Permission.ranking_recalculate,
        Permission.ranking_manage,
        # Audit
        Permission.audit_log_view,
        # Notifications
        Permission.notification_view,
        Permission.notification_send,
        # Reports
        Permission.report_view,
        Permission.report_grant,
        Permission.report_export,
        # Config
        Permission.config_view,
        Permission.academic_year_manage,
        Permission.semester_manage,
        Permission.dashboard_view,
    }),

    "tutor": frozenset({
        # Students (only their groups)
        Permission.student_view_group,
        # Attendance
        Permission.attendance_view,
        Permission.attendance_create,
        Permission.attendance_edit,
        # Grades
        Permission.grade_view,
        Permission.grade_create,
        Permission.grade_edit,
        # Feedback
        Permission.feedback_view,
        Permission.feedback_create,
        Permission.feedback_edit,
        Permission.feedback_delete,
        # Penalties
        Permission.penalty_view,
        Permission.penalty_create,
        # Recovery
        Permission.recovery_view,
        Permission.recovery_create,
        # Courses
        Permission.course_view,
        Permission.course_create,
        # Rankings
        Permission.ranking_view,
        # Notifications
        Permission.notification_view_own,
        # Score history (view only)
        Permission.score_history_view,
    }),

    "parent": frozenset({
        # Own children only
        Permission.student_view_children,
        Permission.attendance_view_children,
        Permission.grade_view_children,
        Permission.feedback_view_children,
        Permission.penalty_view_children,
        Permission.recovery_view_children,
        Permission.achievement_view_own,
        Permission.ranking_view_children,
        Permission.score_history_view_children,
        Permission.notification_view_own,
    }),

    "student": frozenset({
        # Own data only
        Permission.student_view_own,
        Permission.attendance_view_own,
        Permission.grade_view_own,
        Permission.feedback_view_own,
        Permission.penalty_view_own,
        Permission.recovery_view_own,
        Permission.recovery_create,
        Permission.achievement_view_own,
        Permission.achievement_create,
        Permission.achievement_delete,
        Permission.employment_view_own,
        Permission.employment_create,
        Permission.ranking_view_own,
        Permission.score_history_view_own,
        Permission.notification_view_own,
    }),
}


def get_role_permissions(role: str) -> frozenset[str]:
    """Get default permissions for a role."""
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(user_permissions: list[str], required: str) -> bool:
    """Check if a permission is in the user's permission list."""
    return required in user_permissions


def has_any_permission(user_permissions: list[str], *required: str) -> bool:
    """Check if the user has ANY of the required permissions."""
    return any(p in user_permissions for p in required)


def has_all_permissions(user_permissions: list[str], *required: str) -> bool:
    """Check if the user has ALL of the required permissions."""
    return all(p in user_permissions for p in required)
