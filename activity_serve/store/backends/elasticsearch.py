"""Elasticsearch-backed storage for activity objects using AsyncElasticsearch."""

import hashlib
import os
from typing import Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_scan

from activity_serve.store.interfaces import StorageBackend
from activity_serve.store.query import Query


def _doc_id(object_id: str) -> str:
    """Produce a safe Elasticsearch document id from an object id (which may be a URL)."""
    return hashlib.sha256(object_id.encode()).hexdigest()


def _collection_doc_id(object_id: str, collection: str) -> str:
    """Produce a unique document id for a collection membership entry."""
    raw = f"{collection}::{object_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


class ElasticsearchBackend(StorageBackend):
    """Stores activity objects in Elasticsearch."""

    def __init__(
        self,
        url: Optional[str] = None,
        index_prefix: str = "activity_store",
    ):
        self.url = url or os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")
        self.index_prefix = index_prefix
        self.objects_index = f"{index_prefix}_objects"
        self.collections_index = f"{index_prefix}_collections"
        self.client = AsyncElasticsearch(self.url)

    async def setup(self) -> None:
        """Create indices if they don't already exist."""
        for index in (self.objects_index, self.collections_index):
            if not await self.client.indices.exists(index=index):
                await self.client.indices.create(index=index)

    async def teardown(self) -> None:
        """Delete both indices, removing all data."""
        for index in (self.objects_index, self.collections_index):
            if await self.client.indices.exists(index=index):
                await self.client.indices.delete(index=index)

    async def add(self, obj: dict, collection: Optional[str] = None) -> None:
        """Store an object, optionally associating it with a collection."""
        object_id = obj["id"]
        if collection is None:
            await self.client.index(
                index=self.objects_index,
                id=_doc_id(object_id),
                document=obj,
                refresh="wait_for",
            )
        else:
            doc = {**obj, "_collection": collection}
            await self.client.index(
                index=self.collections_index,
                id=_collection_doc_id(object_id, collection),
                document=doc,
                refresh="wait_for",
            )

    async def get(self, object_id: str) -> Optional[dict]:
        """Retrieve an object by its id, or None if not found."""
        try:
            resp = await self.client.get(index=self.objects_index, id=_doc_id(object_id))
        except NotFoundError:
            return None
        return resp["_source"]

    async def remove(self, object_id: str, collection: Optional[str] = None) -> None:
        """Remove an object by id. If collection is given, only remove from that collection."""
        if collection is None:
            try:
                await self.client.delete(
                    index=self.objects_index,
                    id=_doc_id(object_id),
                    refresh="wait_for",
                )
            except NotFoundError:
                pass
        else:
            try:
                await self.client.delete(
                    index=self.collections_index,
                    id=_collection_doc_id(object_id, collection),
                    refresh="wait_for",
                )
            except NotFoundError:
                pass

    async def query(self, query: Query) -> dict:
        """Query stored objects, returning a dict with totalItems and items."""
        if query.collection is not None:
            return await self._query_collection(query)
        return await self._query_objects(query)

    async def _query_objects(self, query: Query) -> dict:
        """Query the main objects index."""
        es_query = self._build_query_body(query)
        resp = await self.client.search(
            index=self.objects_index,
            query=es_query,
            size=query.size,
        )
        total = resp["hits"]["total"]["value"]
        items = [hit["_source"] for hit in resp["hits"]["hits"]]
        return {"totalItems": total, "items": items}

    async def _query_collection(self, query: Query) -> dict:
        """Query the collections index filtered by collection name."""
        must = [{"term": {"_collection.keyword": query.collection}}]

        if query.type is not None:
            if isinstance(query.type, list):
                must.append({"terms": {"type.keyword": query.type}})
            else:
                must.append({"term": {"type.keyword": query.type}})

        if query.text:
            must.append({"multi_match": {"query": query.text, "fields": ["*"]}})

        es_query = {"bool": {"must": must}}
        resp = await self.client.search(
            index=self.collections_index,
            query=es_query,
            size=query.size,
        )
        total = resp["hits"]["total"]["value"]
        items = []
        for hit in resp["hits"]["hits"]:
            source = hit["_source"]
            source.pop("_collection", None)
            items.append(source)
        return {"totalItems": total, "items": items}

    def _build_query_body(self, query: Query) -> dict:
        """Build an Elasticsearch query dict from a Query model."""
        must = []

        if query.type is not None:
            if isinstance(query.type, list):
                must.append({"terms": {"type.keyword": query.type}})
            else:
                must.append({"term": {"type.keyword": query.type}})

        if query.text:
            must.append({"multi_match": {"query": query.text, "fields": ["*"]}})

        if not must:
            return {"match_all": {}}

        return {"bool": {"must": must}}
