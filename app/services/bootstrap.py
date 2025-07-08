from datetime import datetime, UTC
from activity_bus import ActivityBus


async def bootstrap_system() -> None:
    return

    """Bootstrap system collections and namespace objects."""
    store = ActivityBus()

    # Create system namespace collection
    ns_collection = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": "/ns",
        "type": "Collection",
        "name": "Namespace Definitions",
        "summary": "Custom type definitions for the ActivityServe system",
        "published": datetime.now(UTC).isoformat(),
        "items": [],
    }

    await store.store(ns_collection)

    # Create Identity type in namespace
    identity_type = {
        "@context": [
            "https://www.w3.org/ns/activitystreams",
            {"activity-serve": "https://example.org/ns/"},
        ],
        "id": "/ns/Identity",
        "type": "Link",
        "name": "Identity",
        "summary": "Identity links a person to an authentication provider",
        "published": datetime.now(UTC).isoformat(),
    }

    await store.store(identity_type)

    # Create system behaviors collection
    behaviors_collection = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": "/sys/behaviors",
        "type": "Collection",
        "name": "System Behaviors",
        "summary": "Registered behaviors for the ActivityServe system",
        "published": datetime.now(UTC).isoformat(),
        "items": [],
    }

    await store.store(behaviors_collection)
