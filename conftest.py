import pytest
from typing import Dict, Any, AsyncGenerator
from fastapi.testclient import TestClient
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import create_app
from app.services.activity import ActivityComponents, activity_components
from app.core.settings import Settings


@pytest.fixture
def settings():
    """Fixture for test settings."""
    return Settings(
        activity_serve_base_url="http://localhost:8000",
        activity_store_backend="memory",
        activity_store_cache="memory",
        jwt_secret_key="test-secret-key",
        jwt_algorithm="HS256",
        cookie_name="activity_serve_auth",
        cookie_max_age=86400,
    )


@pytest.fixture
def mock_activity_store():
    """Fixture for mocked ActivityStore."""
    mock_store = AsyncMock()
    
    # Define common mock methods
    mock_store.get = AsyncMock(return_value=None)
    mock_store.set = AsyncMock(return_value=None)
    mock_store.query = AsyncMock(return_value=[])
    mock_store.delete = AsyncMock(return_value=None)
    
    return mock_store


@pytest.fixture
def mock_activity_bus():
    """Fixture for mocked ActivityBus."""
    mock_bus = AsyncMock()
    
    # Define common mock methods
    mock_bus.submit = AsyncMock(return_value=None)
    mock_bus.process_next = AsyncMock(return_value=None)
    
    return mock_bus


@pytest.fixture
def patched_activity_components(mock_activity_store, mock_activity_bus):
    """Fixture to patch the global activity components."""
    # Save the original components
    original_store = activity_components.store
    original_bus = activity_components.bus
    
    # Replace with mocks
    activity_components.store = mock_activity_store
    activity_components.bus = mock_activity_bus
    
    yield activity_components
    
    # Restore original components
    activity_components.store = original_store
    activity_components.bus = original_bus


@pytest.fixture
def client(patched_activity_components, settings):
    """Fixture for FastAPI test client."""
    app = create_app()
    
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    """Fixture for authentication headers."""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def mock_user():
    """Fixture for a mock user."""
    return {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": "/u/testuser",
        "type": "Person",
        "name": "Test User",
        "preferredUsername": "testuser",
        "inbox": "/u/testuser/inbox",
        "outbox": "/u/testuser/outbox",
        "published": "2023-01-01T00:00:00Z"
    }


@pytest.fixture
def mock_identity():
    """Fixture for a mock identity."""
    return {
        "@context": ["https://www.w3.org/ns/activitystreams", {"activity-serve": "https://example.org/ns/"}],
        "id": "/u/testuser/idents/google",
        "type": "Identity",
        "provider": "google",
        "sub": "123456789",
        "email": "test@example.com",
        "name": "Test User",
        "user": "/u/testuser",
        "published": "2023-01-01T00:00:00Z"
    }