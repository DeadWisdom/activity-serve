from typing import Any
from fastapi import APIRouter, HTTPException

from activity_serve.store import ActivityStore
from activity_serve.core.utils import first_id, chain_ids, gather
from .auth import UserMaybe

router = APIRouter(tags=["query"])


@router.get("/u/{user_key}/{path:path}")
async def query(user_key: str, path: str, user: UserMaybe, sort: str = "published:desc", after: Any = None):
    """Query a user path item."""

    async with ActivityStore() as store:
        target_user = await store.dereference(f"/u/{user_key}")
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        is_owner = user is not None and target_user["id"] == user["id"]

        item = await store.dereference(f"/u/{user_key}/{path}")
        if item:
            # Check access: owners can always read their own items
            if not is_owner:
                if not await has_audience(store, item.get("audience"), user):
                    raise HTTPException(status_code=403, detail="Forbidden: Item not in audience")

            await populate_collection(store, item, sort, after)
        else:
            # No stored object at this path — check if there's a collection
            # Only the owner can discover implicit collections
            if not is_owner:
                raise HTTPException(status_code=404, detail="Item not found")

            item = {
                "id": f"/u/{user_key}/{path}",
                "type": "OrderedCollection",
            }
            if not await populate_collection(store, item, sort, after):
                raise HTTPException(status_code=404, detail="Item not found")
            item["attributedTo"] = target_user

        return item


async def populate_collection(store: ActivityStore, col: dict, sort: str = "published:desc", after: Any = None):
    """Query the store for items in a collection and populate the dict with results.

    Returns False if the type is not a collection type, or if no items were found.
    """
    col_type = gather(col.get("type"))
    if 'OrderedCollection' not in col_type and 'Collection' not in col_type:
        return False

    result = await store.query(
        collection=col["id"],
        sort=sort,
        after=after,
    )

    items = result.get("items", [])
    total = result.get("totalItems", 0)

    if not items and not total:
        return False

    col["items"] = items
    col["totalItems"] = total
    return True


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
    if audience is None:
        return False

    for collection_id in chain_ids(audience):
        if collection_id in ["Public", "as:Public", "https://www.w3.org/ns/activitystreams#Public"]:
            return True
        user_id = first_id(user)
        if user_id and user_id == collection_id:
            return True

    return False
