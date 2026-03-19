from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables with .env support."""

    # Base URL (will be inferred from request if not set)
    activity_serve_base_url: str | None = None

    # Auth settings
    session_cookie: str = "session"
    session_max_age: int = 86400 * 30  # 30 days in seconds
    session_cookie_httponly: bool = True
    session_cookie_secure: bool = True
    session_cookie_samesite: str = "lax"
    session_cookie_domain: str | None = None

    # Google OAuth verification settings
    google_client_id: str | None = None

    # CORS settings
    allow_origins: list[str] = ["*"]

    model_config = ConfigDict(env_file=".env", case_sensitive=False)
