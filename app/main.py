from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import Settings
from app.api import router as api_router
from app.middleware.logging import LoggingMiddleware
from app.middleware.normalize import NormalizeMiddleware

settings = Settings()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Activity Serve",
        description="ActivityPub-compatible server built with FastAPI",
        version="0.1.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware
    # app.add_middleware(LoggingMiddleware)
    # app.add_middleware(NormalizeMiddleware)

    # Include API routers
    app.include_router(api_router)

    return app


app = create_app()
