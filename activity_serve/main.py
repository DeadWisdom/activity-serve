from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from activity_serve.bus import ActivityBus
from activity_serve.core.settings import Settings
from activity_serve.api.router import create_router
from activity_serve.middleware.logging import LoggingMiddleware
from activity_serve.middleware.normalize import NormalizeMiddleware
from activity_serve.store import ActivityStore

settings = Settings()


def create_app(store: ActivityStore | None = None, bus: ActivityBus | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        store: ActivityStore instance. If None, uses default backends.
        bus: ActivityBus instance. If None, creates one with the given store.
    """
    if store is None:
        store = ActivityStore()
    if bus is None:
        bus = ActivityBus(store=store)

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
    app.include_router(create_router(store, bus))

    return app


app = create_app()
