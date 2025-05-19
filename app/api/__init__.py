from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.user import router as user_router

# Main API router that includes all route modules
router = APIRouter()

# Include all route modules
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(admin_router)
router.include_router(user_router)