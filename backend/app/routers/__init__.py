from fastapi import APIRouter

from app.routers.auth import router as auth_router

router = APIRouter()
router.include_router(auth_router)
