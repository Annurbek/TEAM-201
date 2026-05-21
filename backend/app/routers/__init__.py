from fastapi import APIRouter

from app.routers.auth import router as auth_router
from app.routers.student_router import router as student_router
from app.routers.attendance_router import router as attendance_router
from app.routers.grade_router import router as grade_router
from app.routers.achievement_router import router as achievement_router
from app.routers.feedback_router import router as feedback_router
from app.routers.penalty_router import router as penalty_router
from app.routers.employment_router import router as employment_router
from app.routers.admin_router import router as admin_router
from app.routers.edumetric import router as edumetric_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(student_router)
router.include_router(attendance_router)
router.include_router(grade_router)
router.include_router(achievement_router)
router.include_router(feedback_router)
router.include_router(penalty_router)
router.include_router(employment_router)
router.include_router(admin_router)
router.include_router(edumetric_router)
