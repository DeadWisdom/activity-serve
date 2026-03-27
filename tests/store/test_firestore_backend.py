"""Integration tests for FirestoreBackend requiring a running Firestore emulator."""

import os
import uuid

import pytest

from activity_serve.store.query import Query

pytestmark = pytest.mark.skipif(
    not os.environ.get("FIRESTORE_EMULATOR_HOST"),
    reason="FIRESTORE_EMULATOR_HOST not set",
)


@pytest.fixture
async def firestore_backend():
    from activity_serve.store.backends.firestore import FirestoreBackend

    unique_prefix = f"test_activity_{uuid.uuid4().hex[:8]}"
    backend = FirestoreBackend(collection_prefix=unique_prefix)
    yield backend
    await backend.teardown()


async def test_add_and_get(firestore_backend):
    """Store an object and retrieve it by id."""
    obj = {"id": "https://example.com/1", "type": "Note", "content": "hello"}
    await firestore_backend.add(obj)

    result = await firestore_backend.get("https://example.com/1")
    assert result is not None
    assert result["id"] == "https://example.com/1"
    assert result["content"] == "hello"
    assert result["type"] == "Note"


async def test_get_missing_returns_none(firestore_backend):
    """Getting a non-existent id returns None."""
    result = await firestore_backend.get("https://example.com/missing")
    assert result is None


async def test_remove(firestore_backend):
    """Store an object, remove it, get returns None."""
    obj = {"id": "https://example.com/1", "type": "Note"}
    await firestore_backend.add(obj)
    await firestore_backend.remove("https://example.com/1")

    result = await firestore_backend.get("https://example.com/1")
    assert result is None


async def test_add_to_collection(firestore_backend):
    """Store with collection, query by collection returns the object."""
    obj = {"id": "https://example.com/1", "type": "Note", "content": "in collection"}
    await firestore_backend.add(obj, collection="inbox")

    query = Query(collection="inbox")
    results = await firestore_backend.query(query)
    assert results["totalItems"] == 1
    assert results["items"][0]["id"] == "https://example.com/1"


async def test_remove_from_collection(firestore_backend):
    """Add to collection, remove from collection, query returns empty."""
    obj = {"id": "https://example.com/1", "type": "Note"}
    await firestore_backend.add(obj, collection="inbox")
    await firestore_backend.remove("https://example.com/1", collection="inbox")

    query = Query(collection="inbox")
    results = await firestore_backend.query(query)
    assert results["totalItems"] == 0


async def test_query_by_type(firestore_backend):
    """Store objects of different types, filter by type returns correct ones."""
    note = {"id": "https://example.com/1", "type": "Note", "content": "a note"}
    article = {"id": "https://example.com/2", "type": "Article", "content": "an article"}
    await firestore_backend.add(note)
    await firestore_backend.add(article)

    query = Query(type="Note")
    results = await firestore_backend.query(query)
    assert results["totalItems"] == 1
    assert results["items"][0]["type"] == "Note"


async def test_query_by_type_list(firestore_backend):
    """Query with a list of types returns objects matching any of them."""
    note = {"id": "https://example.com/1", "type": "Note"}
    article = {"id": "https://example.com/2", "type": "Article"}
    event = {"id": "https://example.com/3", "type": "Event"}
    await firestore_backend.add(note)
    await firestore_backend.add(article)
    await firestore_backend.add(event)

    query = Query(type=["Note", "Article"])
    results = await firestore_backend.query(query)
    assert results["totalItems"] == 2
    returned_types = {item["type"] for item in results["items"]}
    assert returned_types == {"Note", "Article"}


async def test_query_size_limit(firestore_backend):
    """Query with size limit returns at most that many items."""
    for i in range(5):
        obj = {"id": f"https://example.com/{i}", "type": "Note", "content": f"note {i}"}
        await firestore_backend.add(obj)

    query = Query(size=2)
    results = await firestore_backend.query(query)
    assert len(results["items"]) == 2


async def test_query_collection_with_type_filter(firestore_backend):
    """Query a collection filtered by type."""
    note = {"id": "https://example.com/1", "type": "Note"}
    article = {"id": "https://example.com/2", "type": "Article"}
    await firestore_backend.add(note, collection="inbox")
    await firestore_backend.add(article, collection="inbox")

    query = Query(collection="inbox", type="Note")
    results = await firestore_backend.query(query)
    assert results["totalItems"] == 1
    assert results["items"][0]["type"] == "Note"


async def test_teardown(firestore_backend):
    """Teardown clears all data."""
    obj = {"id": "https://example.com/1", "type": "Note"}
    await firestore_backend.add(obj)
    await firestore_backend.add(obj, collection="inbox")
    await firestore_backend.teardown()

    result = await firestore_backend.get("https://example.com/1")
    assert result is None

    query = Query(collection="inbox")
    results = await firestore_backend.query(query)
    assert results["totalItems"] == 0
