"""Custom exceptions for the activity store."""


class ActivityStoreError(Exception):
    """Base exception for all activity store errors."""
    pass


class InvalidLDObject(ActivityStoreError):
    """Raised when a linked data object is invalid or missing required fields."""
    pass
