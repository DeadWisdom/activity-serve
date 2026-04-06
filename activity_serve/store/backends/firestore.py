"""Firestore-backed storage for activity objects using the async Firestore client."""

import base64
import hashlib
import os
import re
from typing import Optional

from google.cloud.firestore_v1.async_client import AsyncClient
from google.cloud.firestore_v1.base_query import FieldFilter

from activity_serve.store.interfaces import StorageBackend
from activity_serve.store.query import Query

_URL_SCHEME_RE = re.compile(r"^https?://")


def _short_hash(value: str) -> str:
    """Produce a compact, URL-safe hash of a string for use as a Firestore document key."""
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _id_to_path(object_id: str) -> tuple[str, ...]:
    """Convert an object id into a Firestore document path (alternating collection/doc segments).

    - Path-based ids like "/users/ted" become ("users", "ted").
    - URL ids like "https://firemark.social/users/ted" become ("sites", "firemark.social", "users", "ted").

    Raises ValueError if the resulting path has an odd number of segments.
    """
    stripped = _URL_SCHEME_RE.sub("", object_id)
    is_url = stripped != object_id

    # Remove leading/trailing slashes and split
    parts = tuple(p for p in stripped.split("/") if p)

    if is_url:
        parts = ("sites",) + parts

    if len(parts) % 2 != 0:
        raise ValueError(
            f"Object id must resolve to an even number of path segments, "
            f"got {len(parts)} from '{object_id}'"
        )

    return parts


def _collection_doc_key(object_id: str, collection_parts: tuple[str, ...]) -> str:
    """Determine the document key for an object within a collection.

    If the object id path starts with the collection path, the natural last
    segment is used as the key. Otherwise, the object id is hashed.
    """
    try:
        id_parts = _id_to_path(object_id)
    except ValueError:
        return _short_hash(object_id)

    # If the id is a direct child of the collection, use the natural key
    if id_parts[:-1] == collection_parts and len(id_parts) == len(collection_parts) + 1:
        return id_parts[-1]

    return _short_hash(object_id)


def _normalize_collection(collection: str) -> tuple[str, ...]:
    """Normalize a collection path string into Firestore path segments.

    Applies the same URL-to-path transformation as _id_to_path:
    URLs get their scheme stripped and a "sites/" prefix added.
    """
    stripped = _URL_SCHEME_RE.sub("", collection)
    is_url = stripped != collection

    parts = tuple(p for p in stripped.split("/") if p)

    if is_url:
        parts = ("sites",) + parts

    return parts


class FirestoreBackend(StorageBackend):
    """Stores activity objects in Google Cloud Firestore."""

    def __init__(
        self,
        project: str | None = None,
        database: str | None = None,
    ):
        self.project = project or os.environ.get("FIRESTORE_PROJECT", "activity-serve")
        self.client = AsyncClient(project=self.project, database=database)

    async def teardown(self) -> None:
        """Delete all documents and collections."""
        async for col_ref in self.client.collections():
            await self.client.recursive_delete(col_ref)

    async def add(self, obj: dict, collection: Optional[str] = None) -> None:
        """Store an object, optionally adding it to a collection.

        Canonical storage (collection=None) places the object at its id-derived
        Firestore path. Collection storage places it under the collection path
        with a key derived from the object id.
        """
        object_id = obj["id"]

        if collection is None:
            path = _id_to_path(object_id)
            doc_ref = self.client.document(*path)
            await doc_ref.set(obj)
        else:
            col_parts = _normalize_collection(collection)
            key = _collection_doc_key(object_id, col_parts)
            col_ref = self.client.collection("/".join(col_parts))
            await col_ref.document(key).set(obj)

    async def get(self, object_id: str) -> Optional[dict]:
        """Retrieve a canonically stored object by its id, or None if not found."""
        path = _id_to_path(object_id)
        doc = await self.client.document(*path).get()
        if not doc.exists:
            return None
        return doc.to_dict()

    async def remove(self, object_id: str, collection: Optional[str] = None) -> None:
        """Remove an object by id. If collection is given, only remove from that collection."""
        if collection is None:
            path = _id_to_path(object_id)
            await self.client.document(*path).delete()
        else:
            col_parts = _normalize_collection(collection)
            key = _collection_doc_key(object_id, col_parts)
            col_ref = self.client.collection("/".join(col_parts))
            await col_ref.document(key).delete()

    async def query(self, query: Query) -> dict:
        """Query stored objects, returning a dict with totalItems and items."""
        if query.collection is None:
            return {"totalItems": 0, "items": []}
        return await self._query_collection(query)

    async def _query_collection(self, query: Query) -> dict:
        """Query a Firestore collection with optional type filter, sort, and cursor."""
        col_parts = _normalize_collection(query.collection)
        q = self.client.collection("/".join(col_parts))

        # Type filter
        if query.type is not None:
            if isinstance(query.type, list):
                q = q.where(filter=FieldFilter("type", "in", query.type))
            else:
                q = q.where(filter=FieldFilter("type", "==", query.type))

        # Sort (e.g., "published:desc" or "published:asc")
        if query.sort:
            parts = query.sort.split(":")
            field = parts[0]
            from google.cloud.firestore_v1 import query as fquery
            direction = fquery.Query.DESCENDING if len(parts) > 1 and parts[1].lower() == "desc" else fquery.Query.ASCENDING
            q = q.order_by(field, direction=direction)

            # Cursor pagination — "after" is the value to start after
            if query.after:
                q = q.start_after({field: query.after})

        # Limit
        q = q.limit(query.size)

        docs = [doc async for doc in q.stream()]
        items = [doc.to_dict() for doc in docs]
        return {"totalItems": len(items), "items": items}
