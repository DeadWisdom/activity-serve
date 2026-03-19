"""Tests for convert_to_tombstone on ActivityStore."""

import pytest

from activity_serve.store import ActivityStore
from activity_serve.store.backends.memory import InMemoryStorageBackend, InMemoryCacheBackend


@pytest.fixture
async def store():
    backend = InMemoryStorageBackend()
    cache = InMemoryCacheBackend()
    s = ActivityStore(backend=backend, cache=cache)
    yield s
    await s.teardown(delete_all_backend_data=True)


def _make_note(id="https://example.com/note/1"):
    return {
        "id": id,
        "type": "Note",
        "content": "Hello world",
    }


@pytest.mark.asyncio(loop_scope="function")
async def test_converts_to_tombstone_type(store):
    """convert_to_tombstone changes the type to Tombstone."""
    note = _make_note()
    tombstone = await store.convert_to_tombstone(note)
    assert tombstone["type"] == "Tombstone"


@pytest.mark.asyncio(loop_scope="function")
async def test_preserves_former_type(store):
    """convert_to_tombstone preserves the original type as formerType."""
    note = _make_note()
    tombstone = await store.convert_to_tombstone(note)
    assert tombstone["formerType"] == "Note"


@pytest.mark.asyncio(loop_scope="function")
async def test_sets_deleted_timestamp(store):
    """convert_to_tombstone sets a deleted timestamp."""
    note = _make_note()
    tombstone = await store.convert_to_tombstone(note)
    assert "deleted" in tombstone
    # The deleted timestamp should be an ISO format string ending with Z
    assert tombstone["deleted"].endswith("Z")


@pytest.mark.asyncio(loop_scope="function")
async def test_tombstone_is_stored(store):
    """convert_to_tombstone stores the tombstone so it can be dereferenced."""
    note = _make_note()
    await store.convert_to_tombstone(note)

    result = await store.dereference("https://example.com/note/1")
    assert result is not None
    assert result["type"] == "Tombstone"
    assert result["formerType"] == "Note"


@pytest.mark.asyncio(loop_scope="function")
async def test_tombstone_preserves_id(store):
    """convert_to_tombstone preserves the original object's id."""
    note = _make_note()
    tombstone = await store.convert_to_tombstone(note)
    assert tombstone["id"] == "https://example.com/note/1"


@pytest.mark.asyncio(loop_scope="function")
async def test_tombstone_has_context(store):
    """convert_to_tombstone ensures the tombstone has an @context."""
    note = _make_note()
    tombstone = await store.convert_to_tombstone(note)
    assert "@context" in tombstone
    assert tombstone["@context"] == "https://www.w3.org/ns/activitystreams"
