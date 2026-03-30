"""Tests for the create_router factory function."""

from fastapi import FastAPI
from fastapi.routing import APIRouter
from fastapi.testclient import TestClient

from activity_serve.store import ActivityStore
from activity_serve.store.backends.memory import InMemoryStorageBackend, InMemoryCacheBackend
from activity_serve.bus import ActivityBus
from activity_serve.api.router import create_router
from activity_serve.api.auth import add_stock_token

from .helpers import assert_response

# Stock token for testing auth in the factory router
_factory_token = "factory-test-token-abc123"
_factory_claims = {
    "sub": "factory-user-1",
    "iss": "https://example.com/",
    "email": "factory@example.com",
    "name": "Factory User",
    "picture": "https://example.com/pic.jpg",
}
add_stock_token(_factory_token, _factory_claims)


def _make_app(store=None, bus=None):
    """Create a minimal FastAPI app with the factory router."""
    if store is None:
        store = ActivityStore(
            backend=InMemoryStorageBackend(),
            cache=InMemoryCacheBackend(),
        )
    if bus is None:
        bus = ActivityBus(store=store)
    router = create_router(store, bus)
    app = FastAPI()
    app.include_router(router)
    return app, store, bus


def test_create_router_returns_api_router():
    """create_router returns a FastAPI APIRouter."""
    store = ActivityStore(
        backend=InMemoryStorageBackend(),
        cache=InMemoryCacheBackend(),
    )
    bus = ActivityBus(store=store)
    router = create_router(store, bus)
    assert isinstance(router, APIRouter)


def test_create_router_health_endpoint():
    """The factory router serves the health endpoint."""
    app, _, _ = _make_app()
    with TestClient(app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200


def test_create_router_uses_provided_store():
    """Routes read from the specific store provided to the factory."""
    store = ActivityStore(
        backend=InMemoryStorageBackend(),
        cache=InMemoryCacheBackend(),
    )
    bus = ActivityBus(store=store)
    app, _, _ = _make_app(store, bus)

    auth = {"Authorization": f"Bearer {_factory_token}"}
    with TestClient(app) as client:
        # Create user via /me
        user = client.get("/me", headers=auth).json()
        assert user["type"] == "Person"

        # Verify data is in our specific store
        response = client.get(user["outbox"], headers=auth)
        assert response.status_code == 200


def test_create_router_outbox_uses_provided_bus():
    """Posting to the outbox uses the provided bus instance."""
    store = ActivityStore(
        backend=InMemoryStorageBackend(),
        cache=InMemoryCacheBackend(),
    )
    bus = ActivityBus(store=store)
    app, _, _ = _make_app(store, bus)

    auth = {"Authorization": f"Bearer {_factory_token}"}
    with TestClient(app) as client:
        user = client.get("/me", headers=auth).json()

        response = client.post(
            user["outbox"],
            headers=auth,
            json={"type": "Create", "actor": user["id"], "object": {"type": "Note", "content": "test"}},
        )
        assert response.status_code == 201
        result = response.json()

        # The bus processed it (queue drained) and the activity is in the store
        assert bus.queue.qsize() == 0
        assert result["type"] == "Create"


def test_library_usage_pattern():
    """Full end-to-end: create store, bus, router, mount, post activity, query back."""
    store = ActivityStore(
        backend=InMemoryStorageBackend(),
        cache=InMemoryCacheBackend(),
    )
    bus = ActivityBus(store=store)
    router = create_router(store, bus)

    app = FastAPI()
    app.include_router(router)

    auth = {"Authorization": f"Bearer {_factory_token}"}
    with TestClient(app) as client:
        # Create user
        user = client.get("/me", headers=auth).json()
        assert "outbox" in user

        # Post an activity
        activity = {
            "type": "Create",
            "actor": user["id"],
            "object": {"type": "Note", "content": "Library test!"},
        }
        post_resp = client.post(user["outbox"], headers=auth, json=activity)
        assert post_resp.status_code == 201
        created = post_resp.json()
        assert created["type"] == "Create"

        # Query it back from the outbox
        outbox_resp = client.get(user["outbox"], headers=auth)
        assert outbox_resp.status_code == 200
        outbox = outbox_resp.json()
        assert outbox["totalItems"] == 1
        assert outbox["items"][0]["type"] == "Create"
