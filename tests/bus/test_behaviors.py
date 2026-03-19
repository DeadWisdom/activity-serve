"""Tests for the @when decorator and get_all_behaviors."""

import pytest

from activity_serve.bus.behaviors import when, get_all_behaviors
from activity_serve.bus.registry import registry


@pytest.fixture(autouse=True)
def clear_registry():
    """Reset the global registry before each test."""
    registry.clear()
    yield
    registry.clear()


def test_when_registers_in_registry():
    """Decorating a function with @when registers it in the global registry."""

    @when({"type": "Create"})
    def handle_create(activity):
        return activity

    assert registry.get(handle_create._behavior_id) is handle_create


def test_when_auto_generates_id():
    """@when auto-generates an ID from module.function_name."""

    @when({"type": "Create"})
    def handle_create(activity):
        return activity

    assert handle_create._behavior_id == "/sys/behaviors/test_behaviors.handle_create"


def test_when_custom_id_overrides():
    """Passing id= to @when overrides the auto-generated ID."""
    custom_id = "/sys/behaviors/custom/my_behavior"

    @when({"type": "Create"}, id=custom_id)
    def handle_create(activity):
        return activity

    assert handle_create._behavior_id == custom_id
    assert registry.get(custom_id) is handle_create


def test_get_all_behaviors_returns_with_when_patterns():
    """get_all_behaviors returns behavior dicts with 'when' patterns."""

    @when({"type": "Create"})
    def handle_create(activity):
        return activity

    @when({"type": "Delete"})
    def handle_delete(activity):
        return activity

    behaviors = get_all_behaviors()

    assert len(behaviors) == 2

    for bid, bdata in behaviors.items():
        assert bdata["id"] == bid
        assert bdata["type"] == "Behavior"
        assert "when" in bdata
        assert "_function" in bdata


def test_decorated_function_still_callable():
    """A @when-decorated function can still be called normally."""

    @when({"type": "Test"})
    def process(activity):
        activity["processed"] = True
        return activity

    result = process({"type": "Test"})
    assert result["processed"] is True
