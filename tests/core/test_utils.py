from activity_serve.core.utils import (
    chain,
    chain_ids,
    chain_urls,
    first,
    first_id,
    gather,
    gather_urls,
)


def test_chain_single_values():
    assert list(chain("a", "b", "c")) == ["a", "b", "c"]


def test_chain_flattens_lists():
    assert list(chain("a", ["b", "c"], "d")) == ["a", "b", "c", "d"]


def test_chain_skips_none():
    assert list(chain("a", None, "b")) == ["a", "b"]


def test_chain_nested_lists():
    assert list(chain(["a", ["b", "c"]], "d")) == ["a", "b", "c", "d"]


def test_chain_preserves_dicts():
    d = {"key": "value"}
    assert list(chain(d)) == [d]


def test_chain_ids_from_strings():
    assert list(chain_ids("http://example.com/1", "http://example.com/2")) == [
        "http://example.com/1",
        "http://example.com/2",
    ]


def test_chain_ids_from_objects():
    assert list(chain_ids({"id": "http://example.com/1"}, {"id": "http://example.com/2"})) == [
        "http://example.com/1",
        "http://example.com/2",
    ]


def test_chain_ids_mixed():
    assert list(chain_ids("http://example.com/1", {"id": "http://example.com/2"})) == [
        "http://example.com/1",
        "http://example.com/2",
    ]


def test_chain_urls_from_strings():
    assert list(chain_urls("http://example.com/1")) == ["http://example.com/1"]


def test_chain_urls_from_links():
    assert list(chain_urls({"href": "http://example.com/1"})) == ["http://example.com/1"]


def test_first():
    assert first("a", "b") == "a"
    assert first(None, "b") == "b"
    assert first(None, None) is None
    assert first(["a", "b"]) == "a"


def test_first_id():
    assert first_id("http://example.com/1") == "http://example.com/1"
    assert first_id({"id": "http://example.com/1"}) == "http://example.com/1"
    assert first_id(None) is None


def test_gather():
    assert gather("a", "b") == ["a", "b"]
    assert gather(["a", "b"], "c") == ["a", "b", "c"]
    assert gather(None, "a") == ["a"]


def test_gather_urls():
    assert gather_urls("http://a.com", {"href": "http://b.com"}) == [
        "http://a.com",
        "http://b.com",
    ]
