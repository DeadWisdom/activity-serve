from fastapi.testclient import TestClient
from .helpers import assert_response, make_note


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


def test_history(test_auth, client: TestClient):
    user = client.get("/me", headers=test_auth).json()

    create = {
        "type": "Create",
        "object": {"type": "Note", "content": "Hello, world!"},
    }

    # Send an activity
    client.post(
        user["outbox"],
        headers=test_auth,
        json=create,
    )

    # Get the outbox history
    response = client.get(user["outbox"], headers=test_auth)
    assert_response(response, {"type": "OrderedCollection", "totalItems": 1, "items": [create]})

    update = {
        "type": "Update",
        "object": {"content": "Hello, world!"},
    }

    # Send an activity
    client.post(
        user["outbox"],
        headers=test_auth,
        json=update,
    )

    # Get the outbox history
    response = client.get(user["outbox"], headers=test_auth)
    assert_response(response, {"type": "OrderedCollection", "totalItems": 2, "items": [update]})


def test_outbox_idempotent_resubmit_returns_200(test_auth, client: TestClient):
    """POST same activity with client-provided ID twice: first 201, second 200."""
    user = client.get("/me", headers=test_auth).json()

    activity = {
        "type": "Create",
        "id": f"{user['id']}/activities/idempotent-1",
        "actor": user["id"],
        "object": {"type": "Note", "content": "Hello"},
    }

    first = client.post(user["outbox"], headers=test_auth, json=activity)
    assert first.status_code == 201

    second = client.post(user["outbox"], headers=test_auth, json=activity)
    assert second.status_code == 200
    assert second.json()["id"] == activity["id"]


def test_outbox_conflict_returns_409(test_auth, client: TestClient):
    """POST different content with same ID returns 409."""
    user = client.get("/me", headers=test_auth).json()

    activity_id = f"{user['id']}/activities/conflict-1"

    first = client.post(
        user["outbox"],
        headers=test_auth,
        json={"type": "Create", "id": activity_id, "actor": user["id"], "object": {"type": "Note", "content": "A"}},
    )
    assert first.status_code == 201

    second = client.post(
        user["outbox"],
        headers=test_auth,
        json={"type": "Create", "id": activity_id, "actor": user["id"], "object": {"type": "Note", "content": "B"}},
    )
    assert second.status_code == 409
