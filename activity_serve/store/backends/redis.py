"""Redis-backed cache using async redis and orjson serialization."""

import os
from typing import Any, Optional

import orjson
import redis.asyncio as redis

from activity_serve.store.interfaces import CacheBackend


class RedisCacheBackend(CacheBackend):
    """Cache backend that stores values in Redis with optional TTL support."""

    def __init__(
        self,
        url: Optional[str] = None,
        namespace: str = "activity_store",
    ):
        if url is None:
            url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self._namespace = namespace
        self._redis = redis.from_url(url)

    def _make_key(self, key: str) -> str:
        return f"{self._namespace}:{key}"

    async def add(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Cache a value under the given key with an optional TTL in seconds."""
        data = orjson.dumps(value)
        full_key = self._make_key(key)
        if ttl is not None:
            await self._redis.set(full_key, data, ex=ttl)
        else:
            await self._redis.set(full_key, data)

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value by key, or None if missing or expired."""
        data = await self._redis.get(self._make_key(key))
        if data is None:
            return None
        return orjson.loads(data)

    async def remove(self, key: str) -> None:
        """Remove a cached value by key."""
        await self._redis.delete(self._make_key(key))
