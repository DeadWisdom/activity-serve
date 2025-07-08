import pytest
import os
from httpx import URL
from fastapi.testclient import TestClient
from pathlib import PurePosixPath

# Set test environment variables before any app imports
os.environ["SESSION_COOKIE_SECURE"] = "false"

from app.main import create_app
from app.core.settings import Settings
from app.api.auth import add_stock_token


# Test Users
test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
test_token_dict = {
    "sub": "123456789",
    "iss": "https://example.com/",
    "email": "test@example.com",
    "name": "Test User",
    "picture": "https://example.com/picture.jpg",
}
add_stock_token(test_token, test_token_dict)


@pytest.fixture
def test_auth():
    yield {"Authorization": f"Bearer {test_token}"}


@pytest.fixture
def test_auth_info():
    return test_token_dict


@pytest.fixture
def test_auth_id():
    return PurePosixPath("u", test_token_dict["sub"])


@pytest.fixture
def settings():
    """Fixture for test settings."""
    return Settings(
        session_max_age=86400,
        session_cookie_secure=False,  # Disable secure for testing
    )


@pytest.fixture
def app(settings):
    return create_app()


@pytest.fixture
def client(app):
    """Fixture for FastAPI test client."""

    class EZTestClient(TestClient):
        def _merge_url(self, url: URL | str | PurePosixPath) -> URL:
            if isinstance(url, PurePosixPath):
                url = str(url)
            return super()._merge_url(url)

    with EZTestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    """Fixture for authentication headers."""
    return {"Authorization": "Bearer test-token"}
