from fastapi import APIRouter

from app.routers.auth import router as auth_router
from app.routers.edumetric import router as edumetric_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(edumetric_router)
