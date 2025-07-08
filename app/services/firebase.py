from typing import Any
from firebase_admin import initialize_app, auth

initialize_app()


def verify_id_token(id_token: str) -> dict[str, Any]:
    """Verify a Firebase Auth ID token."""
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        raise ValueError(str(e))
