"""Integration tests for ElasticsearchBackend requiring a running Elasticsearch instance."""

import os
import uuid

import pytest

from activity_serve.store.query import Query

pytestmark = pytest.mark.skipif(
    not os.environ.get("ELASTICSEARCH_URL"),
    reason="ELASTICSEARCH_URL not set",
)


@pytest.fixture
async def es_backend():
    from activity_serve.store.backends.elasticsearch import ElasticsearchBackend

    unique_prefix = f"test_activity_{uuid.uuid4().hex[:8]}"
    url = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")
    backend = ElasticsearchBackend(url=url, index_prefix=unique_prefix)
    await backend.setup()
    yield backend
    await backend.teardown()


async def test_add_and_get(es_backend):
    """Store an object and retrieve it by id."""
    obj = {"id": "https://example.com/1", "type": "Note", "content": "hello"}
    await es_backend.add(obj)

    result = await es_backend.get("https://example.com/1")
    assert result is not None
    assert result["id"] == "https://example.com/1"
    assert result["content"] == "hello"
    assert result["type"] == "Note"


async def test_get_missing_returns_none(es_backend):
    """Getting a non-existent id returns None."""
    result = await es_backend.get("https://example.com/missing")
    assert result is None


async def test_remove(es_backend):
    """Store an object, remove it, get returns None."""
    obj = {"id": "https://example.com/1", "type": "Note"}
    await es_backend.add(obj)
    await es_backend.remove("https://example.com/1")

    result = await es_backend.get("https://example.com/1")
    assert result is None


async def test_add_to_collection(es_backend):
    """Store with collection, query by collection returns the object."""
    obj = {"id": "https://example.com/1", "type": "Note", "content": "in collection"}
    await es_backend.add(obj, collection="inbox")

    query = Query(collection="inbox")
    results = await es_backend.query(query)
    assert results["totalItems"] == 1
    assert results["items"][0]["id"] == "https://example.com/1"


async def test_remove_from_collection(es_backend):
    """Add to collection, remove from collection, query returns empty."""
    obj = {"id": "https://example.com/1", "type": "Note"}
    await es_backend.add(obj, collection="inbox")
    await es_backend.remove("https://example.com/1", collection="inbox")

    query = Query(collection="inbox")
    results = await es_backend.query(query)
    assert results["totalItems"] == 0


async def test_query_by_type(es_backend):
    """Store objects of different types, filter by type returns correct ones."""
    note = {"id": "https://example.com/1", "type": "Note", "content": "a note"}
    article = {"id": "https://example.com/2", "type": "Article", "content": "an article"}
    await es_backend.add(note)
    await es_backend.add(article)

    query = Query(type="Note")
    results = await es_backend.query(query)
    assert results["totalItems"] == 1
    assert results["items"][0]["type"] == "Note"


async def test_query_size_limit(es_backend):
    """Query with size limit returns at most that many items."""
    for i in range(5):
        obj = {"id": f"https://example.com/{i}", "type": "Note", "content": f"note {i}"}
        await es_backend.add(obj)

    query = Query(size=2)
    results = await es_backend.query(query)
    assert results["totalItems"] == 5
    assert len(results["items"]) == 2


async def test_query_text_search(es_backend):
    """Store objects with content, search by text finds matching ones."""
    obj1 = {"id": "https://example.com/1", "type": "Note", "content": "the quick brown fox"}
    obj2 = {"id": "https://example.com/2", "type": "Note", "content": "the lazy dog"}
    await es_backend.add(obj1)
    await es_backend.add(obj2)

    query = Query(text="fox")
    results = await es_backend.query(query)
    assert results["totalItems"] == 1
    assert results["items"][0]["id"] == "https://example.com/1"


async def test_teardown(es_backend):
    """Teardown clears all data."""
    obj = {"id": "https://example.com/1", "type": "Note"}
    await es_backend.add(obj)
    await es_backend.add(obj, collection="inbox")
    await es_backend.teardown()

    # Re-setup so we can query the now-empty indices
    await es_backend.setup()

    result = await es_backend.get("https://example.com/1")
    assert result is None

    query = Query(collection="inbox")
    results = await es_backend.query(query)
    assert results["totalItems"] == 0


async def test_setup_creates_index(es_backend):
    """Setup is idempotent — calling it again does not raise."""
    # es_backend fixture already called setup(), call it again
    await es_backend.setup()

    # Should still work fine
    obj = {"id": "https://example.com/1", "type": "Note"}
    await es_backend.add(obj)
    result = await es_backend.get("https://example.com/1")
    assert result is not None
