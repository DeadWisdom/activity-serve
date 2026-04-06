"""In-memory implementations of StorageBackend and CacheBackend for testing and development."""

import copy
import time
from typing import Any, Optional

from activity_serve.store.interfaces import StorageBackend, CacheBackend
from activity_serve.store.query import Query


class InMemoryStorageBackend(StorageBackend):
    """Stores activity objects in memory using plain dicts."""

    def __init__(self):
        self._objects: dict[str, dict] = {}
        self._collections: dict[str, list[dict]] = {}

    async def add(self, obj: dict, collection: Optional[str] = None) -> None:
        object_id = obj["id"]
        if collection is None:
            self._objects[object_id] = copy.deepcopy(obj)
        else:
            if collection not in self._collections:
                self._collections[collection] = []
            self._collections[collection].append(copy.deepcopy(obj))

    async def get(self, object_id: str) -> Optional[dict]:
        obj = self._objects.get(object_id)
        if obj is not None:
            return copy.deepcopy(obj)
        return None

    async def remove(self, object_id: str, collection: Optional[str] = None) -> None:
        if collection is None:
            self._objects.pop(object_id, None)
        else:
            if collection in self._collections:
                self._collections[collection] = [
                    o for o in self._collections[collection] if o.get("id") != object_id
                ]

    async def query(self, query: Query) -> dict:
        items: list[dict] = []

        if query.collection is not None:
            items = list(self._collections.get(query.collection, []))
        else:
            items = list(self._objects.values())

        if query.type is not None:
            if isinstance(query.type, list):
                items = [o for o in items if o.get("type") in query.type]
            else:
                items = [o for o in items if o.get("type") == query.type]

        # Sort
        if query.sort:
            parts = query.sort.split(":")
            field = parts[0]
            reverse = len(parts) > 1 and parts[1].lower() == "desc"
            items.sort(key=lambda o: o.get(field, ""), reverse=reverse)

        # Cursor pagination
        if query.after and query.sort:
            field = query.sort.split(":")[0]
            items = [o for o in items if o.get(field, "") > query.after] if "desc" not in query.sort else [o for o in items if o.get(field, "") < query.after]

        total = len(items)
        items = items[:query.size]

        return {
            "totalItems": total,
            "items": [copy.deepcopy(o) for o in items],
        }

    async def teardown(self) -> None:
        self._objects.clear()
        self._collections.clear()


class InMemoryCacheBackend(CacheBackend):
    """Caches values in memory with optional TTL support."""

    def __init__(self):
        self._cache: dict[str, dict] = {}

    async def add(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expires_at = None
        if ttl is not None:
            expires_at = time.time() + ttl
        self._cache[key] = {
            "value": copy.deepcopy(value),
            "expires_at": expires_at,
        }

    async def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry is None:
            return None
        if entry["expires_at"] is not None and time.time() >= entry["expires_at"]:
            del self._cache[key]
            return None
        return copy.deepcopy(entry["value"])

    async def remove(self, key: str) -> None:
        self._cache.pop(key, None)
