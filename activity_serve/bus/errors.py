"""Exception classes for the activity bus."""


class ActivityBusError(Exception):
    """Base exception for all activity bus errors."""
    pass


class InvalidActivityError(ActivityBusError):
    """Raised when an activity is missing required fields."""
    pass


class ActivityIdError(InvalidActivityError):
    """Raised when an activity ID is invalid."""
    pass


class BehaviorExecutionError(ActivityBusError):
    """Raised when a behavior function fails during execution."""
    pass


class ActivityExists(ActivityBusError):
    """Raised when an activity with the same ID and content already exists."""

    def __init__(self, existing_activity: dict):
        self.existing_activity = existing_activity
        super().__init__("Activity already exists with identical content")


class ActivityConflict(ActivityBusError):
    """Raised when an activity with the same ID but different content exists."""
    pass
