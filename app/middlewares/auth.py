from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
import structlog
from app.services.auth import verify_auth_token
from app.services.user import get_user_by_id

logger = structlog.get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication from cookie or bearer token."""
    
    def __init__(
        self,
        app,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        cookie_name: str = "activity_serve_auth"
    ):
        super().__init__(app)
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.cookie_name = cookie_name
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Extract token from cookie or Authorization header
        token = self._get_token_from_request(request)
        
        if token:
            # Verify the token
            payload = verify_auth_token(token)
            
            if payload:
                # Get the user ID from the token
                user_id = payload.get("sub")
                
                if user_id:
                    try:
                        # Get the user from the database
                        user = await get_user_by_id(user_id)
                        
                        if user:
                            # Set the user in the request state
                            request.state.user = user
                    except Exception as e:
                        logger.error("Error getting user", error=str(e), user_id=user_id)
        
        # Continue processing the request
        return await call_next(request)
    
    def _get_token_from_request(self, request: Request) -> Optional[str]:
        """Extract token from cookie or Authorization header."""
        # Try to get token from cookie
        token = request.cookies.get(self.cookie_name)
        
        if token:
            return token
        
        # Try to get token from Authorization header
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header.replace("Bearer ", "", 1)
        
        return None