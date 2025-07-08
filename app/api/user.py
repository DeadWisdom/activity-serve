from nanoid import generate
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request, Body

from activity_store import ActivityStore
from activity_store.utils import first_id
from activity_bus import ActivityBus
from .auth import User, UserMaybe


router = APIRouter(tags=["user"])


@router.get("/me")
async def me(user: User):
    """Returns the user info back to them"""
    async with ActivityStore() as store:
        # Get the inbox collection
        return await store.dereference(user["id"])


@router.get("/u/{user_key}/inbox")
async def get_inbox(user_key: str, user: UserMaybe):
    """Get a user's inbox."""
    async with ActivityStore() as store:
        # Get the inbox collection
        inbox = await store.dereference(f"/u/{user_key}/inbox")
        if not inbox:
            raise HTTPException(status_code=404)

        # Return the inbox collection
        return inbox


@router.get("/u/{user_key}/outbox")
async def get_outbox(user_key: str, request: Request):
    """Get a user's outbox."""
    async with ActivityStore() as store:
        # Get the outbox collection
        outbox = await store.dereference(f"/u/{user_key}/outbox")
        if not outbox:
            raise HTTPException(status_code=404)

        # Return the outbox collection
        return outbox


@router.post("/u/{user_key}/outbox")
async def post_to_outbox(
    user_key: str,
    request: Request,
    user: User,
    activity: Dict[str, Any] = Body(...),
):
    """Post a new activity to a user's outbox."""
    # Check if user exists
    async with ActivityStore() as store:
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
            activity["id"] = f"{user['id']}/activities/{generate()}"

        # Submit the activity to the bus
        return await ActivityBus(store=store).submit(activity)
