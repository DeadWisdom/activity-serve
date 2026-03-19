"""Tests for convert_to_tombstone on ActivityStore."""

import pytest

from activity_serve.store import ActivityStore
from activity_serve.store.backends.memory import InMemoryStorageBackend, InMemoryCacheBackend
from tests.helpers import make_note


@pytest.fixture
async def store():
    backend = InMemoryStorageBackend()
    cache = InMemoryCacheBackend()
    s = ActivityStore(backend=backend, cache=cache)
    yield s
    await s.teardown(delete_all_backend_data=True)


async def test_converts_to_tombstone_type(store):
    """convert_to_tombstone changes the type to Tombstone."""
    note = make_note()
    tombstone = await store.convert_to_tombstone(note)
    assert tombstone["type"] == "Tombstone"


async def test_preserves_former_type(store):
    """convert_to_tombstone preserves the original type as formerType."""
    note = make_note()
    tombstone = await store.convert_to_tombstone(note)
    assert tombstone["formerType"] == "Note"


async def test_sets_deleted_timestamp(store):
    """convert_to_tombstone sets a deleted timestamp."""
    note = make_note()
    tombstone = await store.convert_to_tombstone(note)
    assert "deleted" in tombstone
    # The deleted timestamp should be an ISO format string ending with Z
    assert tombstone["deleted"].endswith("Z")


async def test_tombstone_is_stored(store):
    """convert_to_tombstone stores the tombstone so it can be dereferenced."""
    note = make_note()
    await store.convert_to_tombstone(note)

    result = await store.dereference("https://example.com/note/1")
    assert result is not None
    assert result["type"] == "Tombstone"
    assert result["formerType"] == "Note"


async def test_tombstone_preserves_id(store):
    """convert_to_tombstone preserves the original object's id."""
    note = make_note()
    tombstone = await store.convert_to_tombstone(note)
    assert tombstone["id"] == "https://example.com/note/1"


async def test_tombstone_has_context(store):
    """convert_to_tombstone ensures the tombstone has an @context."""
    note = make_note()
    tombstone = await store.convert_to_tombstone(note)
    assert "@context" in tombstone
    assert tombstone["@context"] == "https://www.w3.org/ns/activitystreams"
