from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.settings import Settings
from app.services.activity import init_activity_components
from app.api import router as api_router
from app.middlewares.auth import AuthMiddleware
from app.middlewares.logging import LoggingMiddleware
from app.middlewares.normalize import NormalizeMiddleware
from app.background.worker import start_background_worker

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Bootstrap system collections and namespaces
    from app.services.bootstrap import bootstrap_system
    
    await bootstrap_system()
    
    # Start background worker
    start_background_worker()
    
    yield
    
    # Shutdown logic can be added here if needed


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Activity Serve",
        description="ActivityPub-compatible server built with FastAPI",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middlewares
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        AuthMiddleware,
        jwt_secret=settings.jwt_secret_key,
        jwt_algorithm=settings.jwt_algorithm,
        cookie_name=settings.cookie_name,
    )
    app.add_middleware(NormalizeMiddleware)

    # Initialize activity store and bus
    init_activity_components(settings)

    # Include API routers
    app.include_router(api_router)

    return app


app = create_app()
