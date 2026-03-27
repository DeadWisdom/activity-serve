"""Factory function for creating a FastAPI router with injected store and bus."""

from typing import Any, Annotated, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, ORJSONResponse

from activity_serve.bus import ActivityBus
from activity_serve.bus.errors import ActivityConflict, ActivityExists
from activity_serve.core.utils import first_id, chain_ids, gather
from activity_serve.services.firebase import verify_id_token
from activity_serve.services.user import get_or_create_user
from activity_serve.store import ActivityStore
from activity_serve.store.query import Query

from .auth import verify_auth_token


class ActivityStreamResponse(ORJSONResponse):
    media_type = 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'


def create_router(store: ActivityStore, bus: ActivityBus) -> APIRouter:
    """Return a FastAPI router with inbox/outbox/query endpoints.

    The returned router uses the provided store and bus instances
    via closure, so downstream projects can include_router() it
    with their own backends.
    """
    router = APIRouter(default_response_class=ActivityStreamResponse)

    # --- Auth dependencies that close over the provided store ---

    async def get_user(request: Request):
        auth = request.headers.get("Authorization", "").strip()
        return await get_or_create_user(store, verify_auth_token(auth))

    async def get_user_maybe(request: Request):
        if request.headers.get("Authorization") is None:
            return None
        auth = request.headers.get("Authorization", "").strip()
        return await get_or_create_user(store, verify_auth_token(auth))

    User = Annotated[dict[str, Any], Depends(get_user)]
    UserMaybe = Annotated[dict[str, Any] | None, Depends(get_user_maybe)]

    # --- Health ---

    @router.get("/healthz")
    async def health_check():
        """Health check endpoint to verify service is running."""
        return "ok"

    # --- Admin ---

    @router.get("/admin", response_class=HTMLResponse)
    async def admin_ui():
        """Return a simple HTML admin UI shell."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Activity Serve Admin</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    line-height: 1.6;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                }
                h1 {
                    color: #333;
                }
                .placeholder {
                    background-color: #f5f5f5;
                    padding: 20px;
                    border-radius: 5px;
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Activity Serve Admin</h1>
                <div class="placeholder">
                    <p>This is a placeholder for the admin UI. Future versions will include a full admin interface.</p>
                    <p>You can use this space to build a custom admin interface for your Activity Serve instance.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html_content

    # --- User ---

    @router.get("/me")
    async def me(user: User):
        """Returns the user info back to them."""
        return await store.dereference(user["id"])

    @router.get("/u/{user_key}/inbox")
    async def get_inbox(user_key: str, user: UserMaybe):
        """Get a user's inbox."""
        inbox = await store.dereference(f"/u/{user_key}/inbox")
        if not inbox:
            raise HTTPException(status_code=404)
        return inbox

    @router.get("/u/{user_key}/outbox")
    async def get_outbox(user_key: str, sort: str = "published:desc", after: Any = None):
        """Get a user's outbox."""
        user = await store.dereference(f"/u/{user_key}")
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        outbox = await store.query(
            collection=f"/u/{user_key}/outbox",
            sort=sort,
            after=after,
        )

        outbox['type'] = 'OrderedCollection'
        outbox["attributedTo"] = user
        outbox["audience"] = "Public"
        outbox["id"] = f"/u/{user_key}/outbox"
        return outbox

    @router.post("/u/{user_key}/outbox", status_code=201)
    async def post_to_outbox(
        user_key: str,
        user: User,
        activity: Dict[str, Any] = Body(...),
    ):
        """Post a new activity to a user's outbox."""
        outbox_user = await store.dereference(f"/u/{user_key}")
        if not outbox_user:
            raise HTTPException(status_code=404)

        # Verify that the authenticated user matches the URL user
        if user["id"] != outbox_user["id"]:
            raise HTTPException(status_code=403, detail="You can only post to your own outbox")

        # Inject actor if missing
        if "actor" not in activity:
            activity["actor"] = user["id"]

        # Verify actor matches URL
        if first_id(activity["actor"]) != user["id"]:
            raise HTTPException(status_code=400, detail="Activity actor must match URL user")

        # Generate ID if missing
        if "id" not in activity:
            from nanoid import generate
            activity["id"] = f"{user['id']}/activities/{generate()}"

        # Submit the activity to the bus
        try:
            result = await bus.submit(activity)
        except ActivityExists as e:
            return ORJSONResponse(content=e.existing_activity, status_code=200)
        except ActivityConflict:
            raise HTTPException(status_code=409, detail="Activity with this ID already exists with different content")

        # Add to the outbox collection
        await store.add_to_collection(result, f"/u/{user_key}/outbox")

        return result

    # --- Query ---

    @router.get("/u/{user_key}/{path:path}")
    async def query(user_key: str, path: str, user: UserMaybe, sort: str = "published:desc", after: Any = None):
        """Query a user path item."""
        target_user = await store.dereference(f"/u/{user_key}")
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        is_owner = user is not None and target_user["id"] == user["id"]

        item = await store.dereference(f"/u/{user_key}/{path}")
        if item:
            # Check access: owners can always read their own items
            if not is_owner:
                if not await _has_audience(item.get("audience"), user):
                    raise HTTPException(status_code=403, detail="Forbidden: Item not in audience")

            await _populate_collection(item, sort, after)
        else:
            # No stored object at this path — check if there's a collection
            # Only the owner can discover implicit collections
            if not is_owner:
                raise HTTPException(status_code=404, detail="Item not found")

            item = {
                "id": f"/u/{user_key}/{path}",
                "type": "OrderedCollection",
            }
            if not await _populate_collection(item, sort, after):
                raise HTTPException(status_code=404, detail="Item not found")
            item["attributedTo"] = target_user

        return item

    # --- Query helpers (close over store) ---

    async def _populate_collection(col: dict, sort: str = "published:desc", after: Any = None):
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

    async def _has_audience(audience: Any, user: Any) -> bool:
        """Check the user matches the audience."""
        if audience is None:
            return False

        for collection_id in chain_ids(audience):
            if collection_id in ["Public", "as:Public", "https://www.w3.org/ns/activitystreams#Public"]:
                return True
            user_id = first_id(user)
            if user_id and user_id == collection_id:
                return True

        return False

    return router
