import pytest
from fastapi.testclient import TestClient
from .helpers import assert_response


def test_user_outbox(test_auth, client: TestClient):
    """Test getting an existing outbox."""
    # Ensure the user is created
    user = client.get("/me", headers=test_auth).json()

    # Okay now we can get the box
    response = client.get(user["outbox"], headers=test_auth)
    assert_response(response, {"type": "OrderedCollection"})


def test_send_activity(test_auth, client: TestClient):
    user = client.get("/me", headers=test_auth).json()

    # Send a new activity
    response = client.post(
        user["outbox"],
        headers=test_auth,
        json={"type": "Create", "actor": user["id"], "object": {"type": "Note", "content": "Hello, world!"}},
    )
    assert_response(response, {"type": "Create", "object": {}})
