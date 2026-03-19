import asyncio

from fastapi.testclient import TestClient

from activity_serve.store import ActivityStore


def _run(coro):
    """Run an async coroutine synchronously in tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_query_existing_item(test_auth, client: TestClient):
    """Query a stored object by its path and get it back."""
    user = client.get("/me", headers=test_auth).json()
    user_key = user["id"].split("/u/")[1]

    note = {
        "id": f"/u/{user_key}/notes/1",
        "type": "Note",
        "content": "Hello world",
        "audience": "Public",
    }

    async def setup():
        async with ActivityStore() as store:
            await store.store(note)

    _run(setup())

    response = client.get(f"/u/{user_key}/notes/1", headers=test_auth)
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "Note" or "Note" in data.get("type", [])
    assert "Hello world" in str(data.get("content", ""))


def test_query_nonexistent_user_returns_404(client: TestClient):
    """Query a path for a user that doesn't exist returns 404."""
    response = client.get("/u/nonexistent_user_xyz/notes/1")
    assert response.status_code == 404


def test_query_collection(test_auth, client: TestClient):
    """Query a collection path returns an OrderedCollection with items."""
    user = client.get("/me", headers=test_auth).json()
    user_key = user["id"].split("/u/")[1]

    notes = [
        {"id": f"/u/{user_key}/notes/{i}", "type": "Note", "content": f"Note {i}"}
        for i in range(1, 4)
    ]

    async def setup():
        async with ActivityStore() as store:
            for note in notes:
                await store.add_to_collection(note, f"/u/{user_key}/notes")

    _run(setup())

    response = client.get(f"/u/{user_key}/notes", headers=test_auth)
    assert response.status_code == 200
    data = response.json()
    assert "OrderedCollection" in str(data.get("type", ""))
    assert data.get("totalItems", 0) == 3


def test_query_own_private_item(test_auth, client: TestClient):
    """A user can access their own items regardless of audience."""
    user = client.get("/me", headers=test_auth).json()
    user_key = user["id"].split("/u/")[1]

    private_note = {
        "id": f"/u/{user_key}/notes/private",
        "type": "Note",
        "content": "Secret note",
        "audience": f"/u/{user_key}/followers",
    }

    async def setup():
        async with ActivityStore() as store:
            await store.store(private_note)

    _run(setup())

    # Owner can access their own private item
    response = client.get(f"/u/{user_key}/notes/private", headers=test_auth)
    assert response.status_code == 200
    data = response.json()
    assert "Secret note" in str(data.get("content", ""))


def test_query_public_audience(test_auth, client: TestClient):
    """An item with audience 'Public' is accessible without authentication."""
    user = client.get("/me", headers=test_auth).json()
    user_key = user["id"].split("/u/")[1]

    public_note = {
        "id": f"/u/{user_key}/notes/public",
        "type": "Note",
        "content": "Public note",
        "audience": "Public",
    }

    async def setup():
        async with ActivityStore() as store:
            await store.store(public_note)

    _run(setup())

    # Access without authentication
    response = client.get(f"/u/{user_key}/notes/public")
    assert response.status_code == 200
    data = response.json()
    assert "Public note" in str(data.get("content", ""))


def test_query_private_item_denied_for_non_owner(test_auth, client: TestClient):
    """A non-public item returns 403 for unauthenticated users."""
    user = client.get("/me", headers=test_auth).json()
    user_key = user["id"].split("/u/")[1]

    private_note = {
        "id": f"/u/{user_key}/notes/secret",
        "type": "Note",
        "content": "Top secret",
        "audience": f"/u/{user_key}/followers",
    }

    async def setup():
        async with ActivityStore() as store:
            await store.store(private_note)

    _run(setup())

    # Unauthenticated user gets 403
    response = client.get(f"/u/{user_key}/notes/secret")
    assert response.status_code == 403


def test_query_nonexistent_path_returns_404_for_non_owner(test_auth, client: TestClient):
    """Non-owners cannot discover implicit collections — they get 404."""
    user = client.get("/me", headers=test_auth).json()
    user_key = user["id"].split("/u/")[1]

    # Unauthenticated user trying to discover a collection path
    response = client.get(f"/u/{user_key}/some-collection")
    assert response.status_code == 404
