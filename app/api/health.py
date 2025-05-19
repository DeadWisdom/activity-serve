from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.services.activity import get_activity_store, get_activity_bus


router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = "ok"
    version: str = "0.1.0"


@router.get("/healthz", response_model=HealthResponse)
async def health_check(
    store=Depends(get_activity_store),
    bus=Depends(get_activity_bus)
):
    """Health check endpoint to verify service is running."""
    # The dependencies will raise an exception if not initialized
    return HealthResponse()