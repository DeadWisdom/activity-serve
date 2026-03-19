"""Main ActivityStore class that coordinates storage and caching of activity objects."""

import datetime
from typing import Optional

from activity_serve.store.exceptions import InvalidLDObject
from activity_serve.store.interfaces import StorageBackend, CacheBackend
from activity_serve.store.query import Query

ACTIVITYSTREAMS_CONTEXT = "https://www.w3.org/ns/activitystreams"

# Fields preserved when storing a partial representation in a collection
COLLECTION_FIELDS = {"id", "type", "name", "summary", "url", "published", "updated", "@context"}


class ActivityStore:
    """Coordinates storage and caching of ActivityStreams objects."""

    def __init__(self, backend: StorageBackend, cache: CacheBackend):
        self.backend = backend
        self.cache = cache

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
        """Add the default ActivityStreams context if none is present."""
        if "@context" not in obj:
            obj["@context"] = ACTIVITYSTREAMS_CONTEXT
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

    async def query(self, query: Query) -> dict:
        """Query the backend for objects matching the given criteria."""
        return await self.backend.query(query)

    async def add_to_collection(self, obj, collection: str) -> None:
        """Add an object to a named collection, storing a partial representation."""
        self._validate(obj)
        self._ensure_context(obj)

        # Store the full object in the main store
        await self.backend.add(obj)

        # Build a partial representation for the collection
        partial = {k: v for k, v in obj.items() if k in COLLECTION_FIELDS}
        await self.backend.add(partial, collection=collection)

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
            "@context": ACTIVITYSTREAMS_CONTEXT,
        }
        await self.store(tombstone)
        return tombstone

    async def teardown(self, delete_all_backend_data: bool = False) -> None:
        """Clean up resources. If delete_all_backend_data is True, wipe the backend."""
        if delete_all_backend_data:
            await self.backend.teardown()
