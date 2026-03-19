"""Registry for storing and retrieving behavior functions by ID."""

from collections.abc import Callable


class BehaviorRegistry:
    """Stores behavior functions keyed by a string identifier."""

    def __init__(self):
        self._behaviors: dict[str, Callable] = {}

    def register(self, behavior_id: str, function: Callable) -> None:
        """Register a behavior function under the given ID."""
        self._behaviors[behavior_id] = function

    def get(self, behavior_id: str) -> Callable | None:
        """Return the behavior for the given ID, or None if not found."""
        return self._behaviors.get(behavior_id)

    def clear(self) -> None:
        """Remove all registered behaviors."""
        self._behaviors.clear()

    def all_behaviors(self) -> dict[str, Callable]:
        """Return a copy of all registered behaviors."""
        return dict(self._behaviors)


# Global registry instance used by the @when decorator
registry = BehaviorRegistry()
