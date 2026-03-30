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

    database = f"test_activity_{uuid.uuid4().hex[:8]}"
    backend = FirestoreBackend(database=database)
    yield backend
    await backend.teardown()


# --- Path resolution ---

async def test_add_and_get_path_based_id(firestore_backend):
    """Store an object with a path-based id and retrieve it."""
    obj = {"id": "/users/ted", "type": "Person", "name": "Ted"}
    await firestore_backend.add(obj)

    result = await firestore_backend.get("/users/ted")
    assert result is not None
    assert result["id"] == "/users/ted"
    assert result["name"] == "Ted"


async def test_add_and_get_url_based_id(firestore_backend):
    """URL ids get mapped under sites/ prefix."""
    obj = {"id": "https://firemark.social/users/ted", "type": "Person", "name": "Ted"}
    await firestore_backend.add(obj)

    result = await firestore_backend.get("https://firemark.social/users/ted")
    assert result is not None
    assert result["id"] == "https://firemark.social/users/ted"
    assert result["name"] == "Ted"


async def test_add_and_get_deep_path(firestore_backend):
    """Objects with deeper paths are stored correctly."""
    obj = {"id": "/users/ted/posts/123", "type": "Note", "content": "hello"}
    await firestore_backend.add(obj)

    result = await firestore_backend.get("/users/ted/posts/123")
    assert result is not None
    assert result["content"] == "hello"


async def test_add_odd_segment_id_raises(firestore_backend):
    """Storing an object with an odd-segment path raises ValueError."""
    obj = {"id": "/users", "type": "Collection"}
    with pytest.raises(ValueError, match="even number"):
        await firestore_backend.add(obj)


async def test_get_missing_returns_none(firestore_backend):
    """Getting a non-existent id returns None."""
    result = await firestore_backend.get("/users/missing")
    assert result is None


async def test_remove(firestore_backend):
    """Store an object, remove it, get returns None."""
    obj = {"id": "/users/ted", "type": "Person"}
    await firestore_backend.add(obj)
    await firestore_backend.remove("/users/ted")

    result = await firestore_backend.get("/users/ted")
    assert result is None


# --- Collections ---

async def test_add_to_collection(firestore_backend):
    """Store with collection, query by collection returns the object."""
    obj = {"id": "https://example.com/note/1", "type": "Note", "content": "in collection"}
    await firestore_backend.add(obj, collection="/users/ted/favorites")

    query = Query(collection="/users/ted/favorites")
    results = await firestore_backend.query(query)
    assert results["totalItems"] == 1
    assert results["items"][0]["id"] == "https://example.com/note/1"


async def test_add_and_query_url_based_collection(firestore_backend):
    """Collections with URL paths get the same sites/ prefix treatment as object ids."""
    obj = {"id": "https://firemark.social/users/ted/outbox/abc", "type": "Create"}
    await firestore_backend.add(obj, collection="https://firemark.social/users/ted/outbox")

    query = Query(collection="https://firemark.social/users/ted/outbox")
    results = await firestore_backend.query(query)
    assert results["totalItems"] == 1
    assert results["items"][0]["id"] == "https://firemark.social/users/ted/outbox/abc"


async def test_url_collection_uses_natural_key_for_child(firestore_backend):
    """When an object id is a direct child of a URL-based collection, the natural key is used."""
    from activity_serve.store.backends.firestore import _normalize_collection, _collection_doc_key

    collection = "https://firemark.social/users/ted/outbox"
    object_id = "https://firemark.social/users/ted/outbox/abc"

    col_parts = _normalize_collection(collection)
    key = _collection_doc_key(object_id, col_parts)
    # Should use natural key "abc", not a hash
    assert key == "abc"


async def test_remove_from_url_based_collection(firestore_backend):
    """Remove works with URL-based collection paths."""
    obj = {"id": "https://example.com/1", "type": "Note"}
    await firestore_backend.add(obj, collection="https://firemark.social/users/ted/inbox")
    await firestore_backend.remove("https://example.com/1", collection="https://firemark.social/users/ted/inbox")

    query = Query(collection="https://firemark.social/users/ted/inbox")
    results = await firestore_backend.query(query)
    assert results["totalItems"] == 0


async def test_collection_item_with_matching_prefix(firestore_backend):
    """Object whose id starts with the collection path uses the natural key."""
    obj = {"id": "/users/ted/outbox/abc123", "type": "Create"}
    await firestore_backend.add(obj, collection="/users/ted/outbox")

    query = Query(collection="/users/ted/outbox")
    results = await firestore_backend.query(query)
    assert results["totalItems"] == 1
    assert results["items"][0]["id"] == "/users/ted/outbox/abc123"


async def test_remove_from_collection(firestore_backend):
    """Add to collection, remove from collection, query returns empty."""
    obj = {"id": "https://example.com/1", "type": "Note"}
    await firestore_backend.add(obj, collection="/users/ted/inbox")
    await firestore_backend.remove("https://example.com/1", collection="/users/ted/inbox")

    query = Query(collection="/users/ted/inbox")
    results = await firestore_backend.query(query)
    assert results["totalItems"] == 0


async def test_canonical_and_collection_are_independent(firestore_backend):
    """Canonical storage and collection storage are completely separate."""
    canonical = {"id": "/users/ted/posts/1", "type": "Note", "content": "canonical version"}
    collection_copy = {"id": "/users/ted/posts/1", "type": "Note", "content": "collection version"}

    await firestore_backend.add(canonical)
    await firestore_backend.add(collection_copy, collection="/users/ted/outbox")

    # Canonical get returns the canonical version
    result = await firestore_backend.get("/users/ted/posts/1")
    assert result["content"] == "canonical version"

    # Collection query returns the collection version
    query = Query(collection="/users/ted/outbox")
    results = await firestore_backend.query(query)
    assert results["items"][0]["content"] == "collection version"


# --- Queries ---

async def test_query_collection_by_type(firestore_backend):
    """Query a collection filtered by type."""
    note = {"id": "https://example.com/1", "type": "Note"}
    article = {"id": "https://example.com/2", "type": "Article"}
    await firestore_backend.add(note, collection="/users/ted/inbox")
    await firestore_backend.add(article, collection="/users/ted/inbox")

    query = Query(collection="/users/ted/inbox", type="Note")
    results = await firestore_backend.query(query)
    assert results["totalItems"] == 1
    assert results["items"][0]["type"] == "Note"


async def test_query_collection_by_type_list(firestore_backend):
    """Query with a list of types returns objects matching any of them."""
    note = {"id": "https://example.com/1", "type": "Note"}
    article = {"id": "https://example.com/2", "type": "Article"}
    event = {"id": "https://example.com/3", "type": "Event"}
    await firestore_backend.add(note, collection="/users/ted/inbox")
    await firestore_backend.add(article, collection="/users/ted/inbox")
    await firestore_backend.add(event, collection="/users/ted/inbox")

    query = Query(type=["Note", "Article"], collection="/users/ted/inbox")
    results = await firestore_backend.query(query)
    assert results["totalItems"] == 2
    returned_types = {item["type"] for item in results["items"]}
    assert returned_types == {"Note", "Article"}


async def test_query_size_limit(firestore_backend):
    """Query with size limit returns at most that many items."""
    for i in range(5):
        obj = {"id": f"https://example.com/{i}", "type": "Note", "content": f"note {i}"}
        await firestore_backend.add(obj, collection="/users/ted/inbox")

    query = Query(collection="/users/ted/inbox", size=2)
    results = await firestore_backend.query(query)
    assert len(results["items"]) == 2


async def test_teardown(firestore_backend):
    """Teardown clears all data."""
    obj = {"id": "/users/ted", "type": "Person"}
    await firestore_backend.add(obj)
    await firestore_backend.add(
        {"id": "https://example.com/1", "type": "Note"}, collection="/users/ted/inbox"
    )
    await firestore_backend.teardown()

    result = await firestore_backend.get("/users/ted")
    assert result is None

    query = Query(collection="/users/ted/inbox")
    results = await firestore_backend.query(query)
    assert results["totalItems"] == 0
