from typing import Any, Annotated
from fastapi import Depends, Request, HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED

from app.services.firebase import verify_id_token
from app.services.user import get_or_create_user

# Used for testing or development purposes
_STOCK_TOKENS = {}


def add_stock_token(token: str, data: dict[str, Any]):
    _STOCK_TOKENS[token] = data


def raise_for_unauth(detail):
    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def parse_auth_token(authorization: str) -> str:
    """Parse the authorization token from the request headers."""
    scheme, _, token = authorization.partition(" ")
    scheme = scheme.strip()
    token = token.strip()

    if scheme != "Bearer":
        raise_for_unauth("Invalid authorization header, expected Bearer")

    return scheme, token


def verify_auth_token(authorization: str) -> dict[str, Any]:
    """
    Get the valid data from the provided authorization token.

    Raises an HTTPException if the token is invalid.
    """
    if not authorization:
        raise_for_unauth("Authorization header required")

    _, token = parse_auth_token(authorization)

    if token in _STOCK_TOKENS:
        return _STOCK_TOKENS[token]

    try:
        return verify_id_token(token)
    except Exception as e:
        raise_for_unauth(str(e))


async def get_user(request: Request) -> "User":
    """
    Get the user information from the auth data.
    """
    auth = request.headers.get("Authorization", "").strip()
    return await get_or_create_user(verify_auth_token(auth))


async def get_user_maybe(request: Request) -> "UserMaybe":
    """
    Get the user information from the auth data.
    """
    # Need to check it like this to see if it is there
    if request.headers.get("Authorization") is None:
        return None

    auth = request.headers.get("Authorization", "").strip()
    return await get_or_create_user(verify_auth_token(auth))


User = Annotated[dict[str, Any], Depends(get_user)]
UserMaybe = Annotated[dict[str, Any] | None, Depends(get_user_maybe)]
