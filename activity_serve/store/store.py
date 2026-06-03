"""Main ActivityStore class that coordinates storage and caching of activity objects."""

import datetime
from typing import Optional

from activity_serve.store.exceptions import InvalidLDObject
from activity_serve.store.interfaces import StorageBackend, CacheBackend
from activity_serve.store.query import Query

ACTIVITYSTREAMS_CONTEXT = "https://www.w3.org/ns/activitystreams"



class ActivityStore:
    """Coordinates storage and caching of ActivityStreams objects."""

    _default_backend: StorageBackend | None = None
    _default_cache: CacheBackend | None = None

    @classmethod
    def _get_default_backend(cls) -> StorageBackend:
        if cls._default_backend is None:
            from activity_serve.store.backends.memory import InMemoryStorageBackend
            cls._default_backend = InMemoryStorageBackend()
        return cls._default_backend

    @classmethod
    def _get_default_cache(cls) -> CacheBackend:
        if cls._default_cache is None:
            from activity_serve.store.backends.memory import InMemoryCacheBackend
            cls._default_cache = InMemoryCacheBackend()
        return cls._default_cache

    def __init__(
        self,
        backend: StorageBackend | None = None,
        cache: CacheBackend | None = None,
        default_context=None,
    ):
        self.backend = backend or self._get_default_backend()
        self.cache = cache or self._get_default_cache()
        # The @context stamped onto objects that arrive without one. Apps with
        # custom AS2 types pass their own JSON-LD context here so behaviors that
        # match those types dispatch even for client-posted activities.
        self.default_context = default_context or ACTIVITYSTREAMS_CONTEXT

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    def _validate(self, obj) -> None:
        """Validate that an object has the required fields for an LD object."""
        if not isinstance(obj, dict):
            raise InvalidLDObject("Object must be a dict")
        if "id" not in obj:
            raise InvalidLDObject("Object must have an 'id' field")
        if not isinstance(obj["id"], str):
            raise InvalidLDObject("Object 'id' must be a string")
        if "type" not in obj:
            raise InvalidLDObject("Object must have a 'type' field")

    def _ensure_context(self, obj: dict) -> dict:
        """Add the store's default context if none is present."""
        if "@context" not in obj:
            obj["@context"] = self.default_context
        return obj

    async def store(self, obj) -> str:
        """Validate, normalize, and persist an activity object. Returns the object id."""
        self._validate(obj)
        self._ensure_context(obj)
        await self.backend.add(obj)
        await self.cache.add(obj["id"], obj)
        return obj["id"]

    async def dereference(self, object_id: str) -> Optional[dict]:
        """Look up an object by id, checking cache first, then backend."""
        cached = await self.cache.get(object_id)
        if cached is not None:
            return cached

        obj = await self.backend.get(object_id)
        if obj is not None:
            await self.cache.add(object_id, obj)
        return obj

    async def query(self, query: Query | dict | None = None, **kwargs) -> dict:
        """Query the backend for objects matching the given criteria.

        Accepts a Query object, a dict of parameters, keyword arguments, or a combination.
        Keyword arguments override dict/Query parameters.
        """
        if query is None and not kwargs:
            final_query = Query()
        elif isinstance(query, Query) and not kwargs:
            final_query = query
        else:
            params = {}
            if isinstance(query, dict):
                params.update(query)
            elif isinstance(query, Query):
                params.update(query.model_dump(exclude_none=True))
            params.update(kwargs)
            final_query = Query(**params)
        return await self.backend.query(final_query)

    async def add_to_collection(self, obj, collection: str) -> None:
        """Add an object to a named collection."""
        self._validate(obj)
        self._ensure_context(obj)

        # Store the full object in the main store
        await self.backend.add(obj)

        # Add to the collection
        await self.backend.add(obj, collection=collection)

    async def remove_from_collection(self, object_id: str, collection: str) -> None:
        """Remove an object from a named collection."""
        await self.backend.remove(object_id, collection=collection)

    async def convert_to_tombstone(self, obj: dict) -> dict:
        """Convert an object to a Tombstone, store it, and return it."""
        tombstone = {
            "id": obj["id"],
            "type": "Tombstone",
            "formerType": obj.get("type"),
            "deleted": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "@context": self.default_context,
        }
        await self.store(tombstone)
        return tombstone

    async def teardown(self, delete_all_backend_data: bool = False) -> None:
        """Clean up resources. If delete_all_backend_data is True, wipe the backend."""
        if delete_all_backend_data:
            await self.backend.teardown()
