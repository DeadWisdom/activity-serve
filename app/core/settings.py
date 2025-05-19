from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables with .env support."""
    
    # Base URL (will be inferred from request if not set)
    activity_serve_base_url: str | None = None
    
    # Backend settings
    activity_store_backend: str = "memory"
    activity_store_cache: str = "memory"
    
    # Connection strings (used if backends are set to specific types)
    elasticsearch_url: str | None = None
    redis_url: str | None = None
    
    # Auth settings
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    cookie_name: str = "activity_serve_auth"
    cookie_max_age: int = 86400 * 30  # 30 days in seconds
    
    # Google OAuth verification settings
    google_client_id: str | None = None
    
    # CORS settings
    allow_origins: list[str] = ["*"]
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False
    )