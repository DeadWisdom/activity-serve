import pytest
from fastapi.testclient import TestClient
from .helpers import assert_response


def test_user_inbox(test_auth, client: TestClient):
    """Test getting an existing inbox."""
    # Ensure the user is created
    user = client.get("/me", headers=test_auth).json()

    # Okay now we can get the inbox
    response = client.get(user["inbox"], headers=test_auth)
    assert_response(response, {"type": "OrderedCollection"})
