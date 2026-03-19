"""Tests for collection operations on ActivityStore."""

import pytest

from activity_serve.store import ActivityStore
from activity_serve.store.query import Query
from activity_serve.store.backends.memory import InMemoryStorageBackend, InMemoryCacheBackend


@pytest.fixture
async def store():
    backend = InMemoryStorageBackend()
    cache = InMemoryCacheBackend()
    s = ActivityStore(backend=backend, cache=cache)
    yield s
    await s.teardown(delete_all_backend_data=True)


def _make_note(id="https://example.com/note/1", content="Hello"):
    return {
        "id": id,
        "type": "Note",
        "content": content,
    }


@pytest.mark.asyncio(loop_scope="function")
async def test_add_to_collection(store):
    """Adding an object to a collection makes it queryable in that collection."""
    note = _make_note()
    await store.add_to_collection(note, "inbox")

    results = await store.query(Query(collection="inbox"))
    assert results["totalItems"] == 1
    assert results["items"][0]["id"] == "https://example.com/note/1"


@pytest.mark.asyncio(loop_scope="function")
async def test_remove_from_collection(store):
    """Removing an object from a collection makes it no longer queryable there."""
    note = _make_note()
    await store.add_to_collection(note, "inbox")
    await store.remove_from_collection("https://example.com/note/1", "inbox")

    results = await store.query(Query(collection="inbox"))
    assert results["totalItems"] == 0


@pytest.mark.asyncio(loop_scope="function")
async def test_query_with_collection_filter(store):
    """Querying with a collection filter only returns objects in that collection."""
    note1 = _make_note(id="https://example.com/note/1")
    note2 = _make_note(id="https://example.com/note/2")

    await store.add_to_collection(note1, "inbox")
    await store.add_to_collection(note2, "outbox")

    inbox_results = await store.query(Query(collection="inbox"))
    assert inbox_results["totalItems"] == 1
    assert inbox_results["items"][0]["id"] == "https://example.com/note/1"

    outbox_results = await store.query(Query(collection="outbox"))
    assert outbox_results["totalItems"] == 1
    assert outbox_results["items"][0]["id"] == "https://example.com/note/2"


@pytest.mark.asyncio(loop_scope="function")
async def test_add_to_collection_stores_partial_representation(store):
    """Adding to a collection stores a partial with id and type."""
    note = _make_note()
    note["name"] = "Test Note"
    await store.add_to_collection(note, "inbox")

    results = await store.query(Query(collection="inbox"))
    item = results["items"][0]
    assert item["id"] == "https://example.com/note/1"
    assert item["type"] == "Note"
    assert item.get("name") == "Test Note"
    # content is not in the preserved fields list, so it should not be present
    assert "content" not in item
