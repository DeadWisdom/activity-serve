from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ActivityBase(BaseModel):
    """Base model for ActivityPub objects."""
    context: str = Field(default="https://www.w3.org/ns/activitystreams", alias="@context")
    id: str
    type: str
    
    class Config:
        populate_by_name = True


class Person(ActivityBase):
    """ActivityPub Person object."""
    name: str
    preferred_username: Optional[str] = Field(default=None, alias="preferredUsername")
    inbox: str
    outbox: str
    image: Optional[str] = None
    published: str


class Identity(ActivityBase):
    """Custom Identity object for authentication providers."""
    provider: str
    sub: str
    email: str
    name: str
    picture: Optional[str] = None
    hd: Optional[str] = None
    user: str
    published: str


class Collection(ActivityBase):
    """ActivityPub Collection object."""
    name: str
    summary: Optional[str] = None
    total_items: Optional[int] = Field(default=None, alias="totalItems")
    items: List[Dict[str, Any]] = []
    
    class Config:
        populate_by_name = True


class OrderedCollection(Collection):
    """ActivityPub OrderedCollection object."""
    type: str = "OrderedCollection"
    ordered_items: List[Dict[str, Any]] = Field(default=[], alias="orderedItems")
    
    class Config:
        populate_by_name = True