"""Core ActivityBus class for submitting and processing activities."""

import asyncio
import datetime
import inspect
import traceback
from typing import Any

from activity_serve.core.ld import frame
from activity_serve.store import ActivityStore

from .behaviors import get_all_behaviors
from .errors import ActivityConflict, ActivityExists, BehaviorExecutionError, InvalidActivityError

_SERVER_FIELDS = {"published", "@context", "result", "context"}


def _strip_server_fields(activity: dict) -> dict:
    """Return a copy of the activity without server-assigned fields."""
    return {k: v for k, v in activity.items() if k not in _SERVER_FIELDS}


class ActivityBus:
    """
    Accepts activities, validates them, stores them, and processes them
    by matching against registered behavior patterns.
    """

    def __init__(self, store: ActivityStore | None = None, namespace: str = "activity_bus"):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.store = store
        self.namespace = namespace

    async def submit(self, activity: dict[str, Any]) -> dict[str, Any]:
        """
        Validate, enrich, store, and enqueue an activity.

        Raises InvalidActivityError if actor, type, or id is missing.
        """
        activity = activity.copy()

        if "actor" not in activity:
            raise InvalidActivityError("Activity must contain an 'actor' field")

        if "type" not in activity:
            raise InvalidActivityError("Activity must contain a 'type' field")

        if "id" not in activity:
            raise InvalidActivityError("Activity must have an 'id'")

        # Check for existing activity with same ID (idempotency)
        existing = await self.store.dereference(activity["id"])
        if existing is not None:
            if _strip_server_fields(existing) == _strip_server_fields(activity):
                raise ActivityExists(existing)
            raise ActivityConflict(f"Activity {activity['id']} already exists with different content")

        if "published" not in activity:
            activity["published"] = datetime.datetime.now(datetime.UTC).isoformat()

        if "result" not in activity:
            activity["result"] = []

        await self.store.store(activity)
        self.queue.put_nowait(activity)

        return activity

    async def process_next(self) -> dict[str, Any] | None:
        """
        Dequeue and process the next activity.

        Returns None if the queue is empty.
        """
        try:
            activity = self.queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

        processed = await self.process(activity)
        self.queue.task_done()
        return processed

    async def process(self, activity: dict[str, Any]) -> dict[str, Any]:
        """
        Match the activity against registered behaviors and execute them.

        On behavior error, converts the activity to a Tombstone.
        """
        if "result" not in activity:
            activity["result"] = []

        behaviors = get_all_behaviors()

        for behavior_id, behavior_data in behaviors.items():
            if frame(activity, behavior_data["when"], require_match=True):
                try:
                    function = behavior_data["_function"]
                    result = function(activity)
                    if inspect.isawaitable(result):
                        result = await result

                    if isinstance(result, list):
                        for new_activity in result:
                            if isinstance(new_activity, dict) and "type" in new_activity:
                                if "context" not in new_activity:
                                    new_activity["context"] = activity["id"]
                                try:
                                    await self.submit(new_activity)
                                except ActivityExists:
                                    pass

                except Exception as e:
                    error = {
                        "type": "Error",
                        "content": traceback.format_exc(),
                        "context": activity["id"],
                        "error_type": type(e).__name__,
                    }
                    activity["result"].append(error)

                    tombstone = await self.store.convert_to_tombstone(activity)
                    return tombstone

        await self.store.store(activity)
        return activity
