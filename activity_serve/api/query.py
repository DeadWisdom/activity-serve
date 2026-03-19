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

        item = await store.dereference(f"/u/{user_key}/{path}")
        if item:
            # Check access: owners can always read their own items
            is_owner = user and target_user["id"] == user["id"]
            if not is_owner:
                if not await has_audience(store, item.get("audience"), user):
                    raise HTTPException(status_code=403, detail="Forbidden: Item not in audience")

        if item:
            await populate_collection(store, item, sort, after)
        else:
            item = {
                "id": f"/u/{user_key}/{path}",
                "type": "OrderedCollection",
            }
            if not await populate_collection(store, item, sort, after):
                raise HTTPException(status_code=404, detail="Item not found")
            item["attributedTo"] = target_user
            item["audience"] = "Public"

        return item


def is_subpath(uri: str, base: str) -> bool:
    if not uri or not base:
        return False
    if not base.endswith('/'):
        base += '/'
    return uri.startswith(base)


async def has_read_access(store: ActivityStore, item: Any, user: UserMaybe) -> bool:
    """Check if user has read access to an item."""
    # First check user is the owner of the collection tree
    if user:
        user_id = user['id']
        item_id = first_id(item)
        if item_id:
            if not item_id.endswith('/'):
                item_id += '/'
            if item_id.startswith(user_id):
                return True

    return False


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
    for collection_id in chain_ids(audience):
        if collection_id in ["Public", "as:Public", "https://www.w3.org/ns/activitystreams#Public"]:
            return True
        user_id = first_id(user)
        if user_id:
            col = await store.query(collection=collection_id, keywords={"id": first_id(user_id)})
            if col.get('items'):
                return True
    return False
