from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from activity_serve.api.health import router as health_router
from activity_serve.api.admin import router as admin_router
from activity_serve.api.user import router as user_router
from activity_serve.api.query import router as query_router
from activity_serve.api.router import create_router


class ActivityStreamResponse(ORJSONResponse):
    media_type = 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'


# Main API router that includes all route modules
router = APIRouter(default_response_class=ActivityStreamResponse)

# Include all route modules
router.include_router(health_router)
router.include_router(admin_router)
router.include_router(user_router)
router.include_router(query_router)
