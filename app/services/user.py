import nanoid
import hashlib
import struct
from datetime import datetime, UTC
from typing import Any

from activity_store import ActivityStore


async def get_identity_by_provider(store: ActivityStore, provider: str, sub: str) -> dict[str, Any] | None:
    """Look up an Identity by provider and subject ID."""
    # Query for identities with matching provider and sub
    query = {"type": "Identity", "provider": provider, "sub": sub}

    results = await store.query(query, limit=1)

    if results and len(results) > 0:
        return results[0]

    return None


def get_identity_id(claims: dict[str, Any]) -> str:
    """Generate a unique key for an identity."""
    hsh = hashlib.new("blake2s", digest_size=32)
    hsh.update(claims.get("sub").encode())
    hsh.update(claims.get("iss").encode())
    key = hsh.hexdigest()[:48]
    return f"/auth/identities/{key}"


async def create_user(
    store: ActivityStore, name: str, preferred_username: str = None, image: str = None
) -> dict[str, Any]:
    """Create a new user with generated user-key."""

    # Generate a unique user-key (8-character nanoid)
    user_key = nanoid.generate(size=8)
    user_id = f"/u/{user_key}"

    # Create user object
    now = datetime.now(UTC).isoformat()

    user = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": user_id,
        "type": "Person",
        "name": name,
        "preferredUsername": preferred_username or name,
        "published": now,
    }

    if image:
        user["image"] = image

    # Add inbox and outbox references
    user["inbox"] = f"{user_id}/inbox"
    user["outbox"] = f"{user_id}/outbox"

    # Create the user in the activity store
    await store.store(user)

    # Create inbox and outbox collections
    inbox = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": f"{user_id}/inbox",
        "type": "OrderedCollection",
        "name": "Inbox",
        "published": now,
        "items": [],
    }

    outbox = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": f"{user_id}/outbox",
        "type": "OrderedCollection",
        "name": "Outbox",
        "published": now,
        "items": [],
    }

    await store.store(inbox)
    await store.store(outbox)

    return user


async def create_identity(store: ActivityStore, claims: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    """Create a new identity linked to a user."""

    identity = {
        "@context": [
            "https://www.w3.org/ns/activitystreams",
            {"activity-serve": "https://example.org/ns/"},
        ],
        "id": get_identity_id(claims),
        "type": "Identity",
        "attributedTo": user["id"],
        "published": datetime.now(UTC).isoformat(),
        "claims": claims,
        "image": claims.get("picture"),
        "name": claims.get("name"),
    }

    await store.store(identity)

    return identity


async def get_or_create_user(claims: str) -> dict[str, Any]:
    """Get a user from an OAuth token, create the user if needed."""
    if not claims.get("sub").strip():
        raise ValueError("Auth claims do not include a subject 'sub' field")

    identity_id = get_identity_id(claims)

    async with ActivityStore() as store:
        # Check if user already exists by looking up identity
        identity = await store.dereference(identity_id)
        if identity:
            user = await store.dereference(identity.get("attributedTo"))
            if user:
                return user
            else:
                pass
                # This should not happen, but if it does, just remake everything

        user = await create_user(store, name=claims.get("name"), image=claims.get("picture"))
        identity = await create_identity(
            store=store,
            claims=claims,
            user=user,
        )

        # Return the user
        return user
