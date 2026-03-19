"""Abstract base classes for storage and cache backends."""

from abc import ABC, abstractmethod
from typing import Any, Optional

from activity_serve.store.query import Query


class StorageBackend(ABC):
    """Abstract interface for persistent storage of activity objects."""

    @abstractmethod
    async def add(self, obj: dict, collection: Optional[str] = None) -> None:
        """Store an object, optionally associating it with a collection."""
        ...

    @abstractmethod
    async def get(self, object_id: str) -> Optional[dict]:
        """Retrieve an object by its id, or None if not found."""
        ...

    @abstractmethod
    async def remove(self, object_id: str, collection: Optional[str] = None) -> None:
        """Remove an object by id. If collection is given, only remove from that collection."""
        ...

    @abstractmethod
    async def query(self, query: Query) -> dict:
        """Query stored objects, returning a dict with totalItems and items."""
        ...

    @abstractmethod
    async def teardown(self) -> None:
        """Clean up all data and resources."""
        ...


class CacheBackend(ABC):
    """Abstract interface for caching activity objects."""

    @abstractmethod
    async def add(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Cache a value under the given key with an optional TTL in seconds."""
        ...

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value by key, or None if missing or expired."""
        ...

    @abstractmethod
    async def remove(self, key: str) -> None:
        """Remove a cached value by key."""
        ...
