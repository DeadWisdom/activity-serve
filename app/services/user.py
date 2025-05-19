from datetime import datetime, UTC
import nanoid
from typing import Dict, Any

from app.services.activity import get_activity_store


async def get_identity_by_provider(provider: str, sub: str) -> Dict[str, Any] | None:
    """Look up an Identity by provider and subject ID."""
    store = get_activity_store()
    
    try:
        # Query for identities with matching provider and sub
        query = {
            "type": "Identity",
            "provider": provider,
            "sub": sub
        }
        
        results = await store.query(query, limit=1)
        
        if results and len(results) > 0:
            return results[0]
        
        return None
    except Exception as e:
        print(f"Error in get_identity_by_provider: {str(e)}")
        # For testing purposes, return None when there's an error
        return None


async def get_user_by_id(user_id: str) -> Dict[str, Any] | None:
    """Get a user by their ID."""
    store = get_activity_store()
    
    try:
        user = await store.get(user_id)
        return user
    except Exception:
        return None


async def create_user(name: str, preferred_username: str = None, image: str = None) -> Dict[str, Any]:
    """Create a new user with generated user-key."""
    store = get_activity_store()
    
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
        "published": now
    }
    
    if image:
        user["image"] = image
    
    # Add inbox and outbox references
    user["inbox"] = f"{user_id}/inbox"
    user["outbox"] = f"{user_id}/outbox"
    
    # Create the user in the activity store
    await store.set(user_id, user)
    
    # Create inbox and outbox collections
    inbox = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": f"{user_id}/inbox",
        "type": "OrderedCollection",
        "name": "Inbox",
        "published": now,
        "items": []
    }
    
    outbox = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": f"{user_id}/outbox",
        "type": "OrderedCollection",
        "name": "Outbox",
        "published": now,
        "items": []
    }
    
    await store.set(f"{user_id}/inbox", inbox)
    await store.set(f"{user_id}/outbox", outbox)
    
    return user


async def create_identity(
    user_id: str,
    provider: str,
    sub: str,
    email: str,
    name: str,
    picture: str = None,
    hd: str = None
) -> Dict[str, Any]:
    """Create a new identity linked to a user."""
    store = get_activity_store()
    
    # Extract user key from user_id
    user_key = user_id.split("/")[-1]
    identity_id = f"/u/{user_key}/idents/{provider}"
    
    # Create identity object
    now = datetime.now(UTC).isoformat()
    
    identity = {
        "@context": ["https://www.w3.org/ns/activitystreams", {"activity-serve": "https://example.org/ns/"}],
        "id": identity_id,
        "type": "Identity",
        "provider": provider,
        "sub": sub,
        "email": email,
        "name": name,
        "published": now,
        "user": user_id
    }
    
    if picture:
        identity["picture"] = picture
    
    if hd:
        identity["hd"] = hd
    
    # Create the identity in the activity store
    await store.set(identity_id, identity)
    
    return identity