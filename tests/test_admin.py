from fastapi.testclient import TestClient


def test_admin_ui(client: TestClient, test_auth: dict):
    """Test the admin UI endpoint."""
    response = client.get("/admin", headers=test_auth)

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"

    # Check that response contains expected HTML
    content = response.text
    assert "<title>Activity Serve Admin</title>" in content
    assert "<h1>Activity Serve Admin</h1>" in content
