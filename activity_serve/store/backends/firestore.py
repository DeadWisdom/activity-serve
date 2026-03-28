"""Firestore-backed storage for activity objects using the async Firestore client."""

import hashlib
import os
from typing import Optional

from google.cloud.firestore_v1.async_client import AsyncClient
from google.cloud.firestore_v1.base_query import FieldFilter

from activity_serve.store.interfaces import StorageBackend
from activity_serve.store.query import Query


def _doc_id(object_id: str) -> str:
    """Produce a safe Firestore document id from an object id (which may be a URL)."""
    return hashlib.sha256(object_id.encode()).hexdigest()


def _collection_doc_id(object_id: str, collection: str) -> str:
    """Produce a unique document id for a collection membership entry."""
    raw = f"{collection}::{object_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


class FirestoreBackend(StorageBackend):
    """Stores activity objects in Google Cloud Firestore."""

    def __init__(
        self,
        project: Optional[str] = None,
        collection_prefix: str = "activity_store",
    ):
        self.project = project or os.environ.get("FIRESTORE_PROJECT", "activity-serve")
        self.collection_prefix = collection_prefix
        self.objects_collection = f"{collection_prefix}_objects"
        self.collections_collection = f"{collection_prefix}_collections"
        self.client = AsyncClient(project=self.project)

    async def teardown(self) -> None:
        """Delete all documents from both Firestore collections."""
        for coll_name in (self.objects_collection, self.collections_collection):
            await self._delete_all_docs(coll_name)

    async def _delete_all_docs(self, collection_name: str) -> None:
        """Delete all documents in a Firestore collection."""
        coll_ref = self.client.collection(collection_name)
        batch_size = 100
        while True:
            docs = coll_ref.limit(batch_size)
            doc_snapshots = [doc async for doc in docs.stream()]
            if not doc_snapshots:
                break
            batch = self.client.batch()
            for doc in doc_snapshots:
                batch.delete(doc.reference)
            await batch.commit()

    async def add(self, obj: dict, collection: Optional[str] = None) -> None:
        """Store an object, optionally associating it with a collection.

        When storing to the main collection (no collection arg), any existing
        collection entries for this object are also updated to stay in sync.
        """
        object_id = obj["id"]
        if collection is None:
            doc_ref = self.client.collection(self.objects_collection).document(_doc_id(object_id))
            await doc_ref.set(obj)
        else:
            doc = {**obj, "_collection": collection}
            doc_ref = self.client.collection(self.collections_collection).document(
                _collection_doc_id(object_id, collection)
            )
            await doc_ref.set(doc)

    async def get(self, object_id: str) -> Optional[dict]:
        """Retrieve an object by its id, or None if not found."""
        doc_ref = self.client.collection(self.objects_collection).document(_doc_id(object_id))
        doc = await doc_ref.get()
        if not doc.exists:
            return None
        return doc.to_dict()

    async def remove(self, object_id: str, collection: Optional[str] = None) -> None:
        """Remove an object by id. If collection is given, only remove from that collection."""
        if collection is None:
            doc_ref = self.client.collection(self.objects_collection).document(_doc_id(object_id))
        else:
            doc_ref = self.client.collection(self.collections_collection).document(
                _collection_doc_id(object_id, collection)
            )
        await doc_ref.delete()

    async def query(self, query: Query) -> dict:
        """Query stored objects, returning a dict with totalItems and items."""
        if query.collection is not None:
            return await self._query_collection(query)
        return await self._query_objects(query)

    async def _query_objects(self, query: Query) -> dict:
        """Query the main objects collection."""
        coll_ref = self.client.collection(self.objects_collection)

        if query.type is not None:
            if isinstance(query.type, list):
                coll_ref = coll_ref.where(filter=FieldFilter("type", "in", query.type))
            else:
                coll_ref = coll_ref.where(filter=FieldFilter("type", "==", query.type))

        docs = [doc async for doc in coll_ref.stream()]
        total = len(docs)
        items = [doc.to_dict() for doc in docs[: query.size]]
        return {"totalItems": total, "items": items}

    async def _query_collection(self, query: Query) -> dict:
        """Query the collections collection filtered by collection name."""
        coll_ref = self.client.collection(self.collections_collection)
        coll_ref = coll_ref.where(filter=FieldFilter("_collection", "==", query.collection))

        if query.type is not None:
            if isinstance(query.type, list):
                coll_ref = coll_ref.where(filter=FieldFilter("type", "in", query.type))
            else:
                coll_ref = coll_ref.where(filter=FieldFilter("type", "==", query.type))

        docs = [doc async for doc in coll_ref.stream()]
        total = len(docs)
        items = []
        for doc in docs[: query.size]:
            data = doc.to_dict()
            data.pop("_collection", None)
            items.append(data)
        return {"totalItems": total, "items": items}
