from fastapi import APIRouter, Response, HTTPException
from pydantic import BaseModel

from app.services.auth import login_or_register, create_auth_token
from app.core.settings import Settings

settings = Settings()
router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Request model for login endpoint."""
    token: str


class UserResponse(BaseModel):
    """User response model."""
    id: str
    type: str
    name: str
    preferred_username: str | None = None
    image: str | None = None
    inbox: str | None = None
    outbox: str | None = None


@router.post("/login", response_model=UserResponse)
async def login(request: LoginRequest, response: Response):
    """Login with Google OAuth JWT and return the user information."""
    try:
        # Process login/registration using the Google token
        user = await login_or_register(request.token)
        
        if not user:
            raise HTTPException(status_code=400, detail="Invalid user data")
        
        # Create a JWT for the user
        token = create_auth_token(user["id"])
        
        # Set a cookie with the JWT
        # In tests, secure needs to be False
        response.set_cookie(
            key=settings.cookie_name,
            value=token,
            max_age=settings.cookie_max_age,
            httponly=True,
            secure=False,  # Set to False for tests
            samesite="lax"  # Use lax for tests
        )
        
        # Convert snake_case to camelCase for ActivityPub compatibility
        return UserResponse(
            id=user["id"],
            type=user["type"],
            name=user["name"],
            preferred_username=user.get("preferredUsername"),
            image=user.get("image"),
            inbox=user.get("inbox"),
            outbox=user.get("outbox")
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        print(f"Exception in login: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))