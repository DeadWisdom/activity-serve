"""Tests for the BehaviorRegistry class."""

from activity_serve.bus.registry import BehaviorRegistry


def test_register_and_get():
    """Registering a behavior makes it retrievable by ID."""
    registry = BehaviorRegistry()

    def my_func(activity):
        return activity

    registry.register("/sys/behaviors/test.my_func", my_func)
    assert registry.get("/sys/behaviors/test.my_func") is my_func


def test_get_returns_none_for_missing():
    """Getting an unregistered ID returns None."""
    registry = BehaviorRegistry()
    assert registry.get("nonexistent") is None


def test_clear_removes_all():
    """Clearing the registry removes every registered behavior."""
    registry = BehaviorRegistry()

    registry.register("a", lambda a: a)
    registry.register("b", lambda a: a)
    registry.clear()

    assert registry.get("a") is None
    assert registry.get("b") is None
    assert registry.all_behaviors() == {}


def test_all_behaviors_returns_all_registered():
    """all_behaviors returns a dict of all registered id -> function mappings."""
    registry = BehaviorRegistry()

    fn1 = lambda a: a
    fn2 = lambda a: a

    registry.register("x", fn1)
    registry.register("y", fn2)

    result = registry.all_behaviors()
    assert len(result) == 2
    assert result["x"] is fn1
    assert result["y"] is fn2
