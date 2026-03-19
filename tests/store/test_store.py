"""Tests for the ActivityStore class."""

import pytest

from activity_serve.store import ActivityStore
from activity_serve.store.exceptions import InvalidLDObject
from activity_serve.store.backends.memory import InMemoryStorageBackend, InMemoryCacheBackend
from tests.helpers import make_note


@pytest.fixture
async def store():
    backend = InMemoryStorageBackend()
    cache = InMemoryCacheBackend()
    s = ActivityStore(backend=backend, cache=cache)
    yield s
    await s.teardown(delete_all_backend_data=True)


async def test_store_and_dereference(store):
    """Storing an object with id and type allows it to be dereferenced."""
    note = make_note()
    object_id = await store.store(note)
    assert object_id == "https://example.com/note/1"

    result = await store.dereference("https://example.com/note/1")
    assert result is not None
    assert result["id"] == "https://example.com/note/1"
    assert result["type"] == "Note"
    assert result["content"] == "Hello world"


async def test_dereference_missing_returns_none(store):
    """Dereferencing a non-existent object returns None."""
    result = await store.dereference("https://example.com/does-not-exist")
    assert result is None


async def test_cache_behavior(store):
    """First dereference hits backend and populates cache; second hits cache."""
    note = make_note()
    await store.store(note)

    # Clear the cache so the first dereference must hit the backend
    await store.cache.remove("https://example.com/note/1")

    # First dereference: cache miss, should fetch from backend and populate cache
    result1 = await store.dereference("https://example.com/note/1")
    assert result1 is not None

    # Verify it's now in the cache
    cached = await store.cache.get("https://example.com/note/1")
    assert cached is not None
    assert cached["id"] == "https://example.com/note/1"

    # Remove from backend to prove second dereference uses cache
    await store.backend.remove("https://example.com/note/1")

    # Second dereference: should hit cache
    result2 = await store.dereference("https://example.com/note/1")
    assert result2 is not None
    assert result2["id"] == "https://example.com/note/1"


async def test_context_manager():
    """ActivityStore works as an async context manager."""
    backend = InMemoryStorageBackend()
    cache = InMemoryCacheBackend()
    async with ActivityStore(backend=backend, cache=cache) as s:
        assert isinstance(s, ActivityStore)
        object_id = await s.store(make_note())
        assert object_id == "https://example.com/note/1"


async def test_store_requires_id(store):
    """Storing an object without an id raises InvalidLDObject."""
    with pytest.raises(InvalidLDObject):
        await store.store({"type": "Note"})


async def test_store_requires_type(store):
    """Storing an object without a type raises InvalidLDObject."""
    with pytest.raises(InvalidLDObject):
        await store.store({"id": "https://example.com/note/1"})


async def test_store_requires_string_id(store):
    """Storing an object with a non-string id raises InvalidLDObject."""
    with pytest.raises(InvalidLDObject):
        await store.store({"id": 123, "type": "Note"})


async def test_store_requires_dict(store):
    """Storing a non-dict raises InvalidLDObject."""
    with pytest.raises(InvalidLDObject):
        await store.store("not a dict")


async def test_store_adds_context_if_missing(store):
    """Storing an object without @context adds the default ActivityStreams context."""
    note = make_note()
    assert "@context" not in note
    await store.store(note)

    result = await store.dereference("https://example.com/note/1")
    assert result["@context"] == "https://www.w3.org/ns/activitystreams"


async def test_store_preserves_existing_context(store):
    """Storing an object with an existing @context preserves it."""
    note = make_note()
    note["@context"] = "https://custom.context/v1"
    await store.store(note)

    result = await store.dereference("https://example.com/note/1")
    assert result["@context"] == "https://custom.context/v1"
