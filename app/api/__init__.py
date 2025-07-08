from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from app.api.health import router as health_router
from app.api.admin import router as admin_router

from app.api.user import router as user_router


class ActivityStreamResponse(ORJSONResponse):
    media_type = 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'


# Main API router that includes all route modules
router = APIRouter(default_response_class=ActivityStreamResponse)

# Include all route modules
router.include_router(health_router)
router.include_router(admin_router)
router.include_router(user_router)
