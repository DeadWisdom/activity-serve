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
