"""Tests for the ActivityBus class."""

import pytest

from activity_serve.bus import ActivityBus, when
from activity_serve.bus.behaviors import get_all_behaviors
from activity_serve.bus.registry import registry
from activity_serve.bus.errors import ActivityConflict, ActivityExists, InvalidActivityError, BehaviorExecutionError
from activity_serve.store import ActivityStore
from activity_serve.store.backends.memory import InMemoryStorageBackend, InMemoryCacheBackend


@pytest.fixture(autouse=True)
def clear_registry():
    """Reset the global registry before each test."""
    registry.clear()
    yield
    registry.clear()


@pytest.fixture
def store():
    return ActivityStore(
        backend=InMemoryStorageBackend(),
        cache=InMemoryCacheBackend(),
    )


@pytest.fixture
def bus(store):
    return ActivityBus(store=store)


def _valid_activity(**overrides):
    base = {
        "type": "Create",
        "actor": "https://example.com/users/alice",
        "id": "https://example.com/activities/1",
        "object": {"type": "Note", "content": "Hello"},
    }
    base.update(overrides)
    return base


# --- submit validation ---

async def test_submit_requires_actor(bus):
    """submit raises InvalidActivityError when actor is missing."""
    activity = {"type": "Create", "id": "https://example.com/1"}
    with pytest.raises(InvalidActivityError, match="actor"):
        await bus.submit(activity)


async def test_submit_requires_type(bus):
    """submit raises InvalidActivityError when type is missing."""
    activity = {"actor": "https://example.com/users/alice", "id": "https://example.com/1"}
    with pytest.raises(InvalidActivityError, match="type"):
        await bus.submit(activity)


async def test_submit_requires_id(bus):
    """submit raises InvalidActivityError when id is missing."""
    activity = {"type": "Create", "actor": "https://example.com/users/alice"}
    with pytest.raises(InvalidActivityError, match="id"):
        await bus.submit(activity)


# --- submit stores and enqueues ---

async def test_submit_stores_and_enqueues(bus, store):
    """submit stores the activity and enqueues it for processing."""
    activity = _valid_activity()
    result = await bus.submit(activity)

    # Stored in the backend
    stored = await store.dereference(result["id"])
    assert stored is not None
    assert stored["type"] == "Create"

    # Enqueued
    assert bus.queue.qsize() == 1


async def test_submit_sets_published_if_missing(bus):
    """submit sets a published timestamp when one is not provided."""
    activity = _valid_activity()
    assert "published" not in activity

    result = await bus.submit(activity)
    assert "published" in result


async def test_submit_preserves_existing_published(bus):
    """submit preserves an existing published timestamp."""
    activity = _valid_activity(published="2025-01-01T00:00:00Z")
    result = await bus.submit(activity)
    assert result["published"] == "2025-01-01T00:00:00Z"


async def test_submit_initializes_result(bus):
    """submit initializes the result field to an empty list."""
    activity = _valid_activity()
    result = await bus.submit(activity)
    assert result["result"] == []


# --- process_next ---

async def test_process_next_returns_none_if_empty(bus):
    """process_next returns None when the queue is empty."""
    result = await bus.process_next()
    assert result is None


async def test_process_next_processes_and_returns(bus):
    """process_next dequeues an activity, processes it, and returns it."""
    activity = _valid_activity()
    await bus.submit(activity)

    result = await bus.process_next()
    assert result is not None
    assert result["type"] == "Create"
    assert bus.queue.qsize() == 0


# --- process matching and execution ---

async def test_process_matches_behavior_by_pattern(bus):
    """process uses ld.frame to match activities against behavior patterns."""
    matched = []

    @when({"type": "Create"})
    def on_create(activity):
        matched.append(activity["id"])

    activity = _valid_activity()
    submitted = await bus.submit(activity)
    await bus.process_next()

    assert submitted["id"] in matched


async def test_process_executes_behavior_function(bus):
    """process calls the matched behavior function with the activity."""

    @when({"type": "Create"})
    def on_create(activity):
        activity["result"].append({"type": "Log", "content": "handled"})

    activity = _valid_activity()
    await bus.submit(activity)
    result = await bus.process_next()

    assert any(r.get("content") == "handled" for r in result["result"])


async def test_process_handles_behavior_error(bus, store):
    """process converts activity to a tombstone when a behavior raises."""

    @when({"type": "Create"})
    def on_create(activity):
        raise ValueError("something broke")

    activity = _valid_activity()
    await bus.submit(activity)
    result = await bus.process_next()

    # Should be converted to a Tombstone
    assert result["type"] == "Tombstone"
    assert result["formerType"] == "Create"


# --- async behavior support ---

async def test_process_executes_async_behavior(bus):
    """process calls an async behavior function and awaits it."""

    @when({"type": "Create"})
    async def on_create(activity):
        activity["result"].append({"type": "Log", "content": "async handled"})

    activity = _valid_activity()
    await bus.submit(activity)
    result = await bus.process_next()

    assert any(r.get("content") == "async handled" for r in result["result"])


async def test_process_handles_async_behavior_error(bus, store):
    """process converts activity to a tombstone when an async behavior raises."""

    @when({"type": "Create"})
    async def on_create(activity):
        raise ValueError("async broke")

    activity = _valid_activity()
    await bus.submit(activity)
    result = await bus.process_next()

    assert result["type"] == "Tombstone"
    assert result["formerType"] == "Create"


async def test_sync_and_async_behaviors_coexist(bus):
    """Both sync and async behaviors fire for the same pattern."""
    called = []

    @when({"type": "Create"}, id="/sys/behaviors/sync_one")
    def sync_handler(activity):
        called.append("sync")

    @when({"type": "Create"}, id="/sys/behaviors/async_one")
    async def async_handler(activity):
        called.append("async")

    activity = _valid_activity()
    await bus.submit(activity)
    await bus.process_next()

    assert "sync" in called
    assert "async" in called


# --- idempotency ---

async def test_submit_idempotent_same_content(bus):
    """Submitting the same activity twice raises ActivityExists."""
    activity = _valid_activity()
    await bus.submit(activity)

    with pytest.raises(ActivityExists) as exc_info:
        await bus.submit(activity)

    assert exc_info.value.existing_activity["id"] == activity["id"]


async def test_submit_conflict_different_content(bus):
    """Submitting a different activity with the same ID raises ActivityConflict."""
    activity = _valid_activity()
    await bus.submit(activity)

    different = _valid_activity(object={"type": "Article", "content": "Different"})
    with pytest.raises(ActivityConflict):
        await bus.submit(different)


async def test_submit_ignores_server_fields_in_comparison(bus):
    """Server-assigned fields (published, @context, result) are ignored in comparison."""
    activity = _valid_activity()
    result = await bus.submit(activity)

    # The stored version now has published, @context, result set by the server.
    # Submitting the original (without those fields) should be treated as same content.
    with pytest.raises(ActivityExists):
        await bus.submit(_valid_activity())


async def test_process_handles_activity_exists_in_recursive_submit(bus):
    """When a behavior re-submits an existing activity, the parent is not tombstoned."""
    # First, submit the child activity
    child = _valid_activity(id="https://example.com/activities/child")
    await bus.submit(child)
    await bus.process_next()

    # Register a behavior that tries to submit the same child
    @when({"type": "Update"})
    def on_update(activity):
        return [child]

    parent = _valid_activity(
        id="https://example.com/activities/parent",
        type="Update",
    )
    await bus.submit(parent)
    result = await bus.process_next()

    # Parent should NOT be a tombstone
    assert result["type"] == "Update"
