from typing import Dict, Any
import datetime
import json
from jose import jwt, JWTError

from app.core.settings import Settings
from app.services.activity import get_activity_store
from app.services.user import get_identity_by_provider, get_user_by_id, create_user, create_identity


settings = Settings()


def create_auth_token(user_id: str) -> str:
    """Create a JWT token for a user."""
    expiration = datetime.datetime.utcnow() + datetime.timedelta(seconds=settings.cookie_max_age)
    
    payload = {
        "sub": user_id,
        "exp": expiration
    }
    
    token = jwt.encode(
        payload, 
        settings.jwt_secret_key, 
        algorithm=settings.jwt_algorithm
    )
    
    return token


def verify_auth_token(token: str) -> Dict[str, Any] | None:
    """Verify a JWT token and return the payload."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        return payload
    except JWTError:
        return None


async def verify_google_token(token: str) -> Dict[str, Any] | None:
    """Verify a Google OAuth JWT token."""
    # For real implementation, this would validate with Google's JWKS
    # For now, we'll just decode and assume it's valid
    try:
        # Just decode the token without verification
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except JWTError:
        return None


async def login_or_register(google_token: str) -> Dict[str, Any]:
    """Process login with Google OAuth token, creating user if needed."""
    # Verify the Google token
    google_payload = await verify_google_token(google_token)
    
    if not google_payload:
        raise ValueError("Invalid Google token")
    
    # Extract user information from Google payload
    google_sub = google_payload.get("sub")
    email = google_payload.get("email")
    name = google_payload.get("name")
    picture = google_payload.get("picture")
    hd = google_payload.get("hd")  # G Suite hosted domain
    
    if not google_sub or not email or not name:
        raise ValueError("Missing required user information in token")
    
    # Check if user already exists by looking up identity
    identity = await get_identity_by_provider("google", google_sub)
    
    if identity:
        # User exists, get user from identity
        user_id = identity.get("user")
        user = await get_user_by_id(user_id)
        
        if not user:
            # This should not happen, but if it does, create the user
            user = await create_user(name=name, image=picture)
            
            # Update the identity to point to the new user
            store = get_activity_store()
            identity["user"] = user["id"]
            await store.set(identity["id"], identity)
    else:
        # Create new user
        user = await create_user(name=name, image=picture)
        
        # Create new identity linked to user
        await create_identity(
            user_id=user["id"],
            provider="google",
            sub=google_sub,
            email=email,
            name=name,
            picture=picture,
            hd=hd
        )
    
    # Return the user
    return user