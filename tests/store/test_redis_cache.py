"""Integration tests for RedisCacheBackend. Requires a running Redis instance."""

import asyncio
import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("REDIS_URL"),
    reason="REDIS_URL not set",
)


@pytest.fixture
async def cache():
    """Create a RedisCacheBackend with a test namespace, clean up after use."""
    from activity_serve.store.backends.redis import RedisCacheBackend
    backend = RedisCacheBackend(namespace="test_activity_store")
    yield backend
    # Clean up all keys under the test namespace
    pattern = f"{backend._namespace}:*"
    keys = []
    async for key in backend._redis.scan_iter(match=pattern):
        keys.append(key)
    if keys:
        await backend._redis.delete(*keys)
    await backend._redis.aclose()


async def test_add_and_get(cache):
    """Cache a value, retrieve it."""
    value = {"id": "https://example.com/1", "type": "Note", "content": "hello"}
    await cache.add("key1", value)

    result = await cache.get("key1")
    assert result is not None
    assert result["id"] == "https://example.com/1"
    assert result["content"] == "hello"


async def test_get_missing_returns_none(cache):
    """Get a non-existent key returns None."""
    result = await cache.get("nonexistent_key")
    assert result is None


async def test_remove(cache):
    """Cache, remove, get returns None."""
    value = {"id": "https://example.com/1", "type": "Note"}
    await cache.add("key1", value)
    await cache.remove("key1")

    result = await cache.get("key1")
    assert result is None


async def test_ttl_expiry(cache):
    """Cache with short TTL, wait for expiry, get returns None."""
    value = {"id": "https://example.com/1", "type": "Note"}
    await cache.add("ttl_key", value, ttl=1)

    # Confirm it's there initially
    result = await cache.get("ttl_key")
    assert result is not None

    # Wait for expiry
    await asyncio.sleep(1.5)

    result = await cache.get("ttl_key")
    assert result is None


async def test_overwrite(cache):
    """Cache same key twice, get returns latest value."""
    await cache.add("key1", {"version": 1})
    await cache.add("key1", {"version": 2})

    result = await cache.get("key1")
    assert result == {"version": 2}


async def test_stores_complex_objects(cache):
    """Cache a nested dict with lists, retrieve intact."""
    value = {
        "id": "https://example.com/1",
        "type": "Note",
        "tags": ["python", "redis", "activitypub"],
        "metadata": {
            "author": {"name": "Test User", "url": "https://example.com/user"},
            "counts": [1, 2, 3],
        },
        "published": "2026-03-19T00:00:00Z",
    }
    await cache.add("complex_key", value)

    result = await cache.get("complex_key")
    assert result == value
