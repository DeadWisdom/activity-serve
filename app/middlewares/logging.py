import time
from typing import Callable
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured logging of HTTP requests."""
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.time()
        
        # Extract request details
        method = request.method
        path = request.url.path
        
        # Process the request through the next middleware/endpoint
        try:
            response = await call_next(request)
            
            # Calculate request duration
            duration_ms = round((time.time() - start_time) * 1000)
            
            # Extract user_id from request state if available
            user_id = getattr(request.state, "user", {}).get("id", None)
            
            # Log the request details
            log_data = {
                "method": method,
                "path": path,
                "status": response.status_code,
                "duration_ms": duration_ms
            }
            
            if user_id:
                log_data["user_id"] = user_id
            
            logger.info("HTTP request", **log_data)
            
            return response
        except Exception as e:
            # Calculate request duration
            duration_ms = round((time.time() - start_time) * 1000)
            
            # Log the error
            logger.exception(
                "HTTP request error",
                method=method,
                path=path,
                error=str(e),
                duration_ms=duration_ms
            )
            
            # Re-raise the exception
            raise