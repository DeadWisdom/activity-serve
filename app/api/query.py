from nanoid import generate
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request, Body

from activity_store import ActivityStore
from activity_store.utils import first_id, chain_ids, gather
from activity_bus import ActivityBus
from .auth import User, UserMaybe

router = APIRouter(tags=["query"])

@router.get("/u/{user_key}/{path:path}")
async def query(user_key: str, path: str, user: UserMaybe, sort: str="published:desc", after: Any=None):
    """Query a user path item."""

    async with ActivityStore() as store:
        target_user = await store.dereference(f"/u/{user_key}")
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        id = f"/u/{user_key}/{path}"
        item = await store.dereference(f"/u/{user_key}/{path}")
        if item:
            if target_user["id"] != user["id"]:
                if not await has_audience(store, item.get("audience"), user):
                    raise HTTPException(status_code=403, detail="Forbidden: Item not in audience")

            if not await has_audience(store, item.get("audience", []), item["id"]):
                raise HTTPException(status_code=403, detail="Forbidden: Item not in audience")

        if item:
            await populate_collection(item, user, sort, after)
        else:
            item = {
                "id": f"/u/{user_key}/{path}",
                "type": "OrderedCollection",
            }
            if not await populate_collection(item, user):
                raise HTTPException(status_code=404, detail="Item not found")
            item["attributedTo"] = user
            item["audience"] = "Public"

        return item


async def populate_collection(col: dict, user: UserMaybe, sort: str="published:desc", after: Any=None):
    type = gather(col.get("type"))
    if 'OrderedCollection' in type:
        pass
    elif 'Collection' in type:
        pass
    else:
        return False


async def has_audience(store: ActivityStore, audience: Any, user: Any) -> bool:
    """
    Check the user matches the audience.
    
    Args:
        store: The ActivityStore instance.
        audience: An audience property, one or many strings or nodes.
        user: A string or node.
    
    Returns:
        True if the user is in the audience, False otherwise.
    """
    for collection_id in chain_ids(audience):
        if collection_id in ["Public", "as:Public", "https://www.w3.org/ns/activitystreams#Public"]:
            return True
        user_id = first_id(user)
        if user_id:
            col = await store.query(collection=collection_id, keywords={"id": first_id(user_id)})
            if col.get('items'):
                return True
    return False
