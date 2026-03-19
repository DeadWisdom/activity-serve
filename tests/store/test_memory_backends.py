"""Tests for InMemoryStorageBackend and InMemoryCacheBackend."""

import time
from unittest.mock import patch

import pytest

from activity_serve.store.backends.memory import InMemoryStorageBackend, InMemoryCacheBackend
from activity_serve.store.query import Query


# --- InMemoryStorageBackend tests ---


@pytest.fixture
async def storage_backend():
    backend = InMemoryStorageBackend()
    yield backend
    await backend.teardown()


@pytest.mark.asyncio(loop_scope="function")
async def test_storage_add_and_get(storage_backend):
    """Adding an object allows it to be retrieved by id."""
    obj = {"id": "https://example.com/1", "type": "Note", "content": "hello"}
    await storage_backend.add(obj)

    result = await storage_backend.get("https://example.com/1")
    assert result is not None
    assert result["id"] == "https://example.com/1"
    assert result["content"] == "hello"


@pytest.mark.asyncio(loop_scope="function")
async def test_storage_get_missing_returns_none(storage_backend):
    """Getting a non-existent object returns None."""
    result = await storage_backend.get("https://example.com/missing")
    assert result is None


@pytest.mark.asyncio(loop_scope="function")
async def test_storage_remove(storage_backend):
    """Removing an object makes it no longer retrievable."""
    obj = {"id": "https://example.com/1", "type": "Note"}
    await storage_backend.add(obj)
    await storage_backend.remove("https://example.com/1")

    result = await storage_backend.get("https://example.com/1")
    assert result is None


@pytest.mark.asyncio(loop_scope="function")
async def test_storage_query_by_collection(storage_backend):
    """Querying by collection returns only objects in that collection."""
    obj1 = {"id": "https://example.com/1", "type": "Note"}
    obj2 = {"id": "https://example.com/2", "type": "Note"}

    await storage_backend.add(obj1, collection="inbox")
    await storage_backend.add(obj2, collection="outbox")

    query = Query(collection="inbox")
    results = await storage_backend.query(query)
    assert results["totalItems"] == 1
    assert results["items"][0]["id"] == "https://example.com/1"


@pytest.mark.asyncio(loop_scope="function")
async def test_storage_query_by_type(storage_backend):
    """Querying by type returns only objects of that type."""
    note = {"id": "https://example.com/1", "type": "Note"}
    article = {"id": "https://example.com/2", "type": "Article"}

    await storage_backend.add(note)
    await storage_backend.add(article)

    query = Query(type="Note")
    results = await storage_backend.query(query)
    assert results["totalItems"] == 1
    assert results["items"][0]["type"] == "Note"


@pytest.mark.asyncio(loop_scope="function")
async def test_storage_teardown_clears_data(storage_backend):
    """Teardown removes all stored objects and collections."""
    obj = {"id": "https://example.com/1", "type": "Note"}
    await storage_backend.add(obj, collection="inbox")
    await storage_backend.teardown()

    result = await storage_backend.get("https://example.com/1")
    assert result is None

    query = Query(collection="inbox")
    results = await storage_backend.query(query)
    assert results["totalItems"] == 0


@pytest.mark.asyncio(loop_scope="function")
async def test_storage_remove_from_collection(storage_backend):
    """Removing from a specific collection leaves the object in storage."""
    obj = {"id": "https://example.com/1", "type": "Note"}
    await storage_backend.add(obj)
    await storage_backend.add(obj, collection="inbox")

    await storage_backend.remove("https://example.com/1", collection="inbox")

    # Object still exists in general storage
    result = await storage_backend.get("https://example.com/1")
    assert result is not None

    # But not in the collection
    query = Query(collection="inbox")
    results = await storage_backend.query(query)
    assert results["totalItems"] == 0


# --- InMemoryCacheBackend tests ---


@pytest.fixture
async def cache_backend():
    backend = InMemoryCacheBackend()
    yield backend


@pytest.mark.asyncio(loop_scope="function")
async def test_cache_add_and_get(cache_backend):
    """Adding a value to cache allows it to be retrieved."""
    value = {"id": "https://example.com/1", "type": "Note"}
    await cache_backend.add("key1", value)

    result = await cache_backend.get("key1")
    assert result is not None
    assert result["id"] == "https://example.com/1"


@pytest.mark.asyncio(loop_scope="function")
async def test_cache_get_missing_returns_none(cache_backend):
    """Getting a non-existent key returns None."""
    result = await cache_backend.get("missing_key")
    assert result is None


@pytest.mark.asyncio(loop_scope="function")
async def test_cache_remove(cache_backend):
    """Removing a key makes it no longer retrievable."""
    value = {"id": "https://example.com/1", "type": "Note"}
    await cache_backend.add("key1", value)
    await cache_backend.remove("key1")

    result = await cache_backend.get("key1")
    assert result is None


@pytest.mark.asyncio(loop_scope="function")
async def test_cache_expired_entry_returns_none(cache_backend):
    """Expired cache entries return None on get."""
    value = {"id": "https://example.com/1", "type": "Note"}
    await cache_backend.add("key1", value, ttl=1)

    # Simulate time passing beyond TTL
    with patch("time.time", return_value=time.time() + 2):
        result = await cache_backend.get("key1")
    assert result is None


@pytest.mark.asyncio(loop_scope="function")
async def test_cache_unexpired_entry_returns_value(cache_backend):
    """Cache entries within TTL are returned."""
    value = {"id": "https://example.com/1", "type": "Note"}
    await cache_backend.add("key1", value, ttl=3600)

    result = await cache_backend.get("key1")
    assert result is not None
    assert result["id"] == "https://example.com/1"


@pytest.mark.asyncio(loop_scope="function")
async def test_cache_returns_deep_copy(cache_backend):
    """Cache returns deep copies so external mutations don't affect stored data."""
    value = {"id": "https://example.com/1", "type": "Note", "content": "original"}
    await cache_backend.add("key1", value)

    result = await cache_backend.get("key1")
    result["content"] = "modified"

    result2 = await cache_backend.get("key1")
    assert result2["content"] == "original"
