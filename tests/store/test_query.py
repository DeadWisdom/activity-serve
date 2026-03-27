"""Tests for the Query pydantic model."""

import pytest
from pydantic import ValidationError

from activity_serve.store.query import Query


def test_query_default_values():
    """Query has expected default values."""
    q = Query()
    assert q.text is None
    assert q.keywords is None
    assert q.sort is None
    assert q.size == 10
    assert q.after is None
    assert q.collection is None
    assert q.type is None


def test_query_size_must_be_positive():
    """Query size must be a positive integer."""
    with pytest.raises(ValidationError):
        Query(size=0)

    with pytest.raises(ValidationError):
        Query(size=-1)


def test_query_size_valid():
    """Query accepts valid positive size values."""
    q = Query(size=5)
    assert q.size == 5


def test_query_to_dict_filters_none():
    """to_dict() excludes fields with None values."""
    q = Query(type="Note")
    d = q.to_dict()
    assert "type" in d
    assert d["type"] == "Note"
    assert "text" not in d
    assert "keywords" not in d
    assert "sort" not in d
    assert "after" not in d
    assert "collection" not in d
    # size has a default non-None value so it should be present
    assert "size" in d
    assert d["size"] == 10


def test_query_to_dict_includes_all_set_values():
    """to_dict() includes all non-None fields."""
    q = Query(text="hello", type="Note", collection="inbox", size=20)
    d = q.to_dict()
    assert d == {
        "text": "hello",
        "type": "Note",
        "collection": "inbox",
        "size": 20,
    }


def test_query_type_accepts_string():
    """Query type field accepts a single string."""
    q = Query(type="Note")
    assert q.type == "Note"


def test_query_type_accepts_list():
    """Query type field accepts a list of strings."""
    q = Query(type=["Note", "Article"])
    assert q.type == ["Note", "Article"]


def test_query_keywords_has_description():
    """Keywords field has a description documenting its purpose."""
    field_info = Query.model_fields["keywords"]
    assert field_info.description is not None
    assert len(field_info.description) > 0
