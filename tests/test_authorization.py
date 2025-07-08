import pytest
from fastapi.testclient import TestClient

from app.api.auth import User, UserMaybe


@pytest.fixture
def mock_routes(app):
    @app.get("/protected")
    async def _(user: User):
        return user

    @app.get("/optional")
    async def _(user: UserMaybe):
        return user

    @app.get("/public")
    async def _():
        return None


@pytest.mark.asyncio
async def test_authorization(mock_routes, test_auth, test_auth_info, client: TestClient):
    """Test successful usage of auth token."""

    protected_route = "/protected"
    optional_route = "/optional"
    public_route = "/public"

    # A good token always works
    response = client.get(protected_route, headers=test_auth)
    response.raise_for_status()
    assert response.json()["type"] == "Person"

    response = client.get(optional_route, headers=test_auth)
    response.raise_for_status()
    assert response.json()["type"] == "Person"

    response = client.get(public_route, headers=test_auth)
    response.raise_for_status()

    # No authorization will fail on protected
    response = client.get(protected_route)
    assert response.status_code == 401

    # No authorization is fine with optional
    response = client.get(optional_route)
    response.raise_for_status()
    assert response.json() is None

    # No authorization is fine with public
    response = client.get(public_route)
    response.raise_for_status()

    # All these values fail on protected and optional
    for value in ("", "Bearer", f"Thingy token", "Bearer ", "Bearer NOTVALID"):
        response = client.get(protected_route, headers={"Authorization": value})
        assert response.status_code == 401

        response = client.get(optional_route, headers={"Authorization": value})
        assert response.status_code == 401
