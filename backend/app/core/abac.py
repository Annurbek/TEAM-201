"""Attribute-Based Access Control (ABAC) layer.

Provides object-level access control helpers that check relationships
between the current user and the target resource.

Usage in routers:
    from app.core.abac import (
        student_access_guard,
        tutor_group_guard,
        parent_child_guard,
        admin_or_self_guard,
    )

    @router.get("/students/{student_id}")
    async def student_detail(
        student_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        student = await student_access_guard(current_user, student_id, db)
        ...
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.users import User
from app.models.student import StudentProfile
from app.models.parent import ParentProfile
from app.models.tutor import TutorProfile
from app.models.groups import Group


class AccessDeniedError(HTTPException):
    """Raised when ABAC check fails."""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def student_access_guard(
    current_user: User,
    student_id: int,
    db: AsyncSession,
) -> StudentProfile:
    """Check if current user can access the given student's data.

    Rules:
    - super_admin / admin: full access to all students
    - tutor: access to students in their groups
    - parent: access to their linked children
    - student: access to their own profile only

    Returns the StudentProfile if access is granted.
    Raises HTTPException 403 if denied, 404 if student not found.
    """
    student = await _get_student_or_404(db, student_id)

    if current_user.role in {UserRole.super_admin, UserRole.admin}:
        return student

    if current_user.role in {UserRole.tutor}:
        if await _is_tutor_of_student(current_user, student, db):
            return student
        raise AccessDeniedError("You can only access students from your groups")

    if current_user.role == UserRole.parent:
        if await _is_parent_of_student(current_user, student, db):
            return student
        raise AccessDeniedError("You can only access your children's data")

    if current_user.role == UserRole.student:
        if student.user_id == current_user.id:
            return student
        raise AccessDeniedError("You can only access your own data")

    raise AccessDeniedError("Insufficient permissions")


async def tutor_group_guard(
    current_user: User,
    group_id: int,
    db: AsyncSession,
) -> Group:
    """Check if current user can access the given group.

    Rules:
    - super_admin / admin: full access
    - tutor: access to groups they are assigned to

    Returns the Group if access is granted.
    """
    from app.models.groups import Group as GroupModel
    from app.models.tutor import TutorGroupLink

    group = (await db.execute(select(GroupModel).where(GroupModel.id == group_id))).scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    if current_user.role in {UserRole.super_admin, UserRole.admin}:
        return group

    if current_user.role == UserRole.tutor:
        tutor_profile = (await db.execute(select(TutorProfile).where(TutorProfile.user_id == current_user.id))).scalar_one_or_none()
        if tutor_profile is None:
            raise AccessDeniedError("Tutor profile not found")

        link = (await db.execute(
            select(TutorGroupLink).where(
                TutorGroupLink.tutor_id == tutor_profile.id,
                TutorGroupLink.group_id == group_id,
            )
        )).scalar_one_or_none()
        if link is not None:
            return group

        raise AccessDeniedError("You can only access your assigned groups")

    raise AccessDeniedError("Insufficient permissions")


async def parent_child_guard(
    current_user: User,
    student_id: int,
    db: AsyncSession,
) -> StudentProfile:
    """Check if current parent user can access the given child student.

    Rules:
    - parent: only their linked children (active link)

    Returns the StudentProfile if access is granted.
    """
    if current_user.role != UserRole.parent:
        raise AccessDeniedError("Only parents can use this endpoint")

    student = await _get_student_or_404(db, student_id)

    parent_profile = (await db.execute(select(ParentProfile).where(ParentProfile.user_id == current_user.id))).scalar_one_or_none()
    if parent_profile is None:
        raise AccessDeniedError("Parent profile not found")

    from app.models.student import StudentParentLink

    link = (await db.execute(
        select(StudentParentLink).where(
            StudentParentLink.student_id == student.id,
            StudentParentLink.parent_id == parent_profile.id,
            StudentParentLink.is_active.is_(True),
        )
    )).scalar_one_or_none()

    if link is None:
        raise AccessDeniedError("This student is not linked to your account")

    return student


async def admin_or_self_guard(
    current_user: User,
    target_user_id: int,
    db: AsyncSession,
) -> User:
    """Check if current user can access/modify another user.

    Rules:
    - super_admin: full access to all users
    - admin: access to all users except super_admin
    - any user: access to their own profile

    Returns the target User if access is granted.
    """
    if current_user.id == target_user_id:
        target = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return target

    if current_user.role == UserRole.super_admin:
        target = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return target

    if current_user.role == UserRole.admin:
        target = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if target.role == UserRole.super_admin:
            raise AccessDeniedError("Admins cannot modify super_admin users")
        return target

    raise AccessDeniedError("You can only access your own profile")


async def can_modify_score_history(current_user: User) -> bool:
    """Check if user can modify score history.

    Rules:
    - admin / super_admin: yes
    - user with "score_history.edit" permission: yes
    - others: no
    """
    if current_user.role in {UserRole.admin, UserRole.super_admin}:
        return True

    user_perms = getattr(current_user, "permissions", None) or []
    return "score_history.edit" in user_perms


async def can_assign_admin_role(current_user: User) -> bool:
    """Check if user can assign admin role to other users.

    Only super_admin can assign admin role.
    """
    return current_user.role == UserRole.super_admin


async def can_manage_users(current_user: User, target_role: UserRole | None = None) -> bool:
    """Check if user can manage users with the given target role.

    Rules:
    - super_admin: can manage any role including admin
    - admin: can manage any role except super_admin
    """
    if current_user.role == UserRole.super_admin:
        return True

    if current_user.role == UserRole.admin:
        if target_role == UserRole.super_admin:
            return False
        return True

    return False


async def _get_student_or_404(db: AsyncSession, student_id: int) -> StudentProfile:
    result = await db.execute(
        select(StudentProfile).where(
            or_(StudentProfile.id == student_id, StudentProfile.user_id == student_id)
        )
    )
    student = result.scalar_one_or_none()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


async def _is_tutor_of_student(current_user: User, student: StudentProfile, db: AsyncSession) -> bool:
    from app.models.tutor import TutorGroupLink, TutorProfile

    tutor_profile = (await db.execute(select(TutorProfile).where(TutorProfile.user_id == current_user.id))).scalar_one_or_none()
    if tutor_profile is None:
        return False

    if student.current_group_id is None:
        return False

    link = (await db.execute(
        select(TutorGroupLink).where(
            TutorGroupLink.tutor_id == tutor_profile.id,
            TutorGroupLink.group_id == student.current_group_id,
        )
    )).scalar_one_or_none()

    return link is not None


async def _is_parent_of_student(current_user: User, student: StudentProfile, db: AsyncSession) -> bool:
    from app.models.student import StudentParentLink

    parent_profile = (await db.execute(select(ParentProfile).where(ParentProfile.user_id == current_user.id))).scalar_one_or_none()
    if parent_profile is None:
        return False

    link = (await db.execute(
        select(StudentParentLink).where(
            StudentParentLink.student_id == student.id,
            StudentParentLink.parent_id == parent_profile.id,
            StudentParentLink.is_active.is_(True),
        )
    )).scalar_one_or_none()

    return link is not None
