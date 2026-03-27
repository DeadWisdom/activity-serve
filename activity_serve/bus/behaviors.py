"""Decorator and utilities for defining activity behaviors."""

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any

from .registry import registry


def when(pattern: dict[str, Any], *, id: str | None = None):
    """
    Decorator that registers a function as a behavior triggered when an
    activity matches the given pattern (via JSON-LD framing).
    """

    def decorator(func: Callable):
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

        # Generate ID from module and function name if not provided
        behavior_id = id
        if behavior_id is None:
            module = inspect.getmodule(func)
            module_name = module.__name__.split(".")[-1] if module else "__main__"
            behavior_id = f"/sys/behaviors/{module_name}.{func.__name__}"

        wrapper._when_pattern = pattern
        wrapper._behavior_id = behavior_id

        registry.register(behavior_id, wrapper)
        return wrapper

    return decorator


def get_all_behaviors() -> dict[str, dict[str, Any]]:
    """
    Return all registered behaviors that have a 'when' pattern.

    Each entry is a dict with keys: id, type, when, _function.
    """
    result = {}
    for behavior_id, func in registry.all_behaviors().items():
        if hasattr(func, "_when_pattern"):
            result[behavior_id] = {
                "id": behavior_id,
                "type": "Behavior",
                "when": func._when_pattern,
                "_function": func,
            }
    return result
