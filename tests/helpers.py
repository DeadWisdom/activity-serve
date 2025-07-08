from activity_store.ld import frame


def assert_response(
    response,
    expected,
    status_code=200,
    content_type='application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
):
    """Assert that the response matches the expected structure."""
    if status_code == 200:
        response.raise_for_status()
    else:
        assert response.status_code == status_code
    print(response.json(), expected)
    assert response.headers["content-type"] == content_type
    if not (result := frame(response.json(), expected, require_match=True)):
        print(response)
        print("---")
        print(expected)
        raise AssertionError("Response does not match expected structure")
