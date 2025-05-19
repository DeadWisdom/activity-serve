import json
from typing import Callable, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
import structlog

logger = structlog.get_logger(__name__)


class NormalizeMiddleware(BaseHTTPMiddleware):
    """Middleware for normalizing all incoming and outgoing IDs."""
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Process the request and get the response
        response = await call_next(request)
        
        # Check if the response content type is JSON
        if response.headers.get("content-type") == "application/json":
            # Read the response body
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            # Parse the JSON response
            try:
                json_response = json.loads(response_body.decode("utf-8"))
                
                # Normalize IDs in the JSON response
                normalized_response = self._normalize_ids(json_response)
                
                # Create a new response with normalized IDs
                new_response = Response(
                    content=json.dumps(normalized_response),
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type="application/json"
                )
                
                return new_response
            except json.JSONDecodeError:
                # If the response is not valid JSON, return it as is
                pass
            
            # Reconstruct the original response if we didn't modify it
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
        
        # Return the original response for non-JSON responses
        return response
    
    def _normalize_ids(self, data: Any) -> Any:
        """Normalize all IDs in a JSON structure."""
        if isinstance(data, dict):
            # If it's a dictionary, normalize IDs for each key-value pair
            result = {}
            
            for key, value in data.items():
                # Normalize ID field
                if key == "id" and isinstance(value, str):
                    result[key] = self._normalize_id(value)
                # Normalize ID values in special ActivityPub fields
                elif key in ["actor", "object", "target", "origin", "inReplyTo"] and isinstance(value, str):
                    result[key] = self._normalize_id(value)
                else:
                    # Recursively normalize values
                    result[key] = self._normalize_ids(value)
            
            return result
        elif isinstance(data, list):
            # If it's a list, normalize each item
            return [self._normalize_ids(item) for item in data]
        else:
            # For other types, return as is
            return data
    
    def _normalize_id(self, id_str: str) -> str:
        """Normalize a single ID string."""
        # Remove trailing slashes
        if id_str.endswith("/"):
            id_str = id_str[:-1]
        
        return id_str