# CLAUDE: ignore this file, it's old ideas

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
import structlog
from app.services.auth import verify_auth_token
from app.services.user import get_user_by_id

from typing import Any
from datetime import timedelta
from firebase_admin import auth

logger = structlog.get_logger(__name__)
router = APIRouter()


def verify_id_token(id_token: str) -> dict[str, Any]:
    """Verify a Firebase Auth ID token."""
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        raise ValueError(f"Failed to verify Firebase ID token: {str(e)}")


def create_session_cookie(id_token: str, max_age: int) -> str:
    """Create a Firebase Auth session cookie from an ID token."""
    expires_in = timedelta(seconds=max_age)
    session_cookie = auth.create_session_cookie(id_token, expires_in=expires_in)
    return session_cookie


def verify_session_cookie(cookie: str) -> dict[str, Any]:
    """Verify a Firebase Auth session cookie."""
    try:
        decoded_claims = auth.verify_session_cookie(cookie)
        return decoded_claims
    except Exception as e:
        raise ValueError(f"Invalid cookie session: {str(e)}")


def get_session(request: Request) -> dict[str, Any] | None:
    """
    Return the session data
    """
    ...


@router.post("/auth")
def login(self, request: Request, authorization: Header()):
    """
    Handle user login:
    - Grabs the id token from the Authorization header (Bearer)
    - Verify it with firebase
    - Create a session cookie

    """
    ...


@router.delete("/auth")
def logout(self):
    """
    Removes our session cookie.
    """
    ...


# IMPERATUM: Fix this
Session: Annotated[dict[str, Any], Depends(get_session)]


class FirebaseSessionMiddleware(BaseHTTPMiddleware):
    """Firebase authentication middlewhere."""

    cookie_name: str = "session"
    cookie_domain: str = None
    cookie_secure: bool = True
    cookie_httponly: bool = True
    cookie_samesite: str = "Lax"
    allow_auth_header: bool = False

    def __init__(
        self,
        app,
        cookie_name: str = "session",
        cookie_domain: str = None,
        cookie_secure: bool = True,
        cookie_httponly: bool = True,
        cookie_samesite: str = "Lax",
        allow_auth_header: bool = False,
        max_age: int = None,
    ):
        super().__init__(app)
        self.cookie_name = cookie_name
        self.cookie_domain = cookie_domain
        self.cookie_secure = cookie_secure
        self.cookie_httponly = cookie_httponly
        self.cookie_samesite = cookie_samesite
        self.allow_auth_header = allow_auth_header
        self.max_age = max_age

        app.add_route("/auth", self.login, methods=["POST"])
        app.add_route("/auth", self.logout, methods=["DELETE"])

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """ """
        ...

    def login(self, request: Request, authorization: Header()):
        """
        Handle user login by:
        - looking at the Authorization header for an id token
        - verify it
        """
        ...

    def logout(self):
        """
        Removes our session cookie.
        """
        ...

    def _resume_session(
        self, request: Request, authorization: Header()
    ) -> dict[str, Any] | None:
        """
        Verify the session from the cookie.
        If it's there, save the data into the retrieval via get_session
        If allow_auth_header is True, first check the Authorization header, verify that and use it
        """
        ...

    def _(self, request: Request) -> dict[str, Any] | None:
        """
        Verify the session from the cookie.
        If it's there, save the data into the contextvar for retrieval via get_session
        """
        ...
