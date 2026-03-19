from unittest.mock import patch

from activity_serve.core.ld import (
    expand_property,
    compact_property,
    normalize,
    any_none,
    with_prefixes,
)


def test_with_prefixes_no_prefixes():
    """Test that with_prefixes returns the original context if no prefixes provided."""
    context = "https://www.w3.org/ns/activitystreams"
    result = with_prefixes(context, None)
    assert result == context

    context = ["https://www.w3.org/ns/activitystreams"]
    result = with_prefixes(context, None)
    assert result == context


def test_with_prefixes_adds_prefixes():
    """Test that with_prefixes correctly adds prefixes to context."""
    # String context
    context = "https://www.w3.org/ns/activitystreams"
    prefixes = {"schema": "http://schema.org/"}
    result = with_prefixes(context, prefixes)
    assert result == [context, prefixes]

    # List context
    context = ["https://www.w3.org/ns/activitystreams"]
    result = with_prefixes(context, prefixes)
    assert result == context + [prefixes]


def test_any_none_simple_values():
    """Test any_none with simple values."""
    assert any_none(None) is True
    assert any_none("not none") is False
    assert any_none(123) is False
    assert any_none({}) is False
    assert any_none([]) is False


def test_any_none_nested_dict():
    """Test any_none with nested dictionaries."""
    # No None values
    doc = {"id": "test", "name": "Test Object", "nested": {"key": "value"}}
    assert any_none(doc) is False

    # With None value
    doc = {"id": "test", "name": None, "nested": {"key": "value"}}
    assert any_none(doc) is True

    # With nested None value
    doc = {"id": "test", "name": "Test Object", "nested": {"key": None}}
    assert any_none(doc) is True


def test_any_none_nested_list():
    """Test any_none with nested lists."""
    # No None values
    doc = {"id": "test", "items": ["item1", "item2", {"key": "value"}]}
    assert any_none(doc) is False

    # With None in list
    doc = {"id": "test", "items": ["item1", None, "item2"]}
    assert any_none(doc) is True

    # With None in nested dict in list
    doc = {"id": "test", "items": ["item1", {"key": None}, "item2"]}
    assert any_none(doc) is True


def test_expand_property_single_property():
    """Test expand_property with a single property name."""
    doc = {
        "id": "test",
        "type": "Note",
        "name": "Test Note",
        "tag": "test-tag",
        "attachment": [{"url": "attachment1"}, {"url": "attachment2"}],
        "nested": {"tag": "nested-tag", "items": [{"tag": "item-tag"}]},
    }

    expand_property(doc, "tag")

    assert doc["tag"] == ["test-tag"]
    assert doc["nested"]["tag"] == ["nested-tag"]
    assert doc["nested"]["items"][0]["tag"] == ["item-tag"]

    # Other properties should be unchanged
    assert doc["id"] == "test"
    assert doc["type"] == "Note"
    assert doc["name"] == "Test Note"
    assert isinstance(doc["attachment"], list)


def test_expand_property_multiple_properties():
    """Test expand_property with multiple property names."""
    doc = {
        "id": "test",
        "type": "Note",
        "name": "Test Note",
        "tag": "test-tag",
        "attachment": {"url": "attachment-url"},
    }

    expand_property(doc, ["type", "tag", "attachment"])

    assert doc["type"] == ["Note"]
    assert doc["tag"] == ["test-tag"]
    assert doc["attachment"] == [{"url": "attachment-url"}]

    assert doc["id"] == "test"
    assert doc["name"] == "Test Note"


def test_compact_property_single_property():
    """Test compact_property with a single property name."""
    doc = {
        "id": "test",
        "type": ["Note"],
        "name": "Test Note",
        "tag": ["test-tag", "another-tag"],
        "nested": {"tag": ["nested-tag"], "items": [{"tag": ["item-tag"]}]},
    }

    compact_property(doc, "tag")

    assert doc["tag"] == "test-tag"
    assert doc["nested"]["tag"] == "nested-tag"
    assert doc["nested"]["items"][0]["tag"] == "item-tag"

    assert doc["id"] == "test"
    assert doc["type"] == ["Note"]
    assert doc["name"] == "Test Note"


def test_compact_property_multiple_properties():
    """Test compact_property with multiple property names."""
    doc = {
        "id": "test",
        "type": ["Note", "Article"],
        "name": "Test Note",
        "tag": ["test-tag", "another-tag"],
        "attachment": [{"url": "attachment-url"}],
    }

    compact_property(doc, ["type", "tag", "attachment"])

    assert doc["type"] == "Note"
    assert doc["tag"] == "test-tag"
    assert doc["attachment"] == {"url": "attachment-url"}

    assert doc["id"] == "test"
    assert doc["name"] == "Test Note"


@patch("activity_serve.core.ld.jsonld.compact")
def test_normalize(mock_compact):
    """Test normalize function."""
    mock_result = {"@graph": [{"id": "test", "type": "Note", "name": "Test Note"}]}
    mock_compact.return_value = mock_result

    doc = {"id": "test", "type": "Note"}
    result = normalize(doc)

    mock_compact.assert_called_once()
    args = mock_compact.call_args[0]
    assert args[0] == doc
    assert args[1] == "https://www.w3.org/ns/activitystreams"

    options = mock_compact.call_args[0][2]
    assert options["compactArrays"] is False

    assert result == {"id": "test", "type": ["Note"], "name": "Test Note"}


@patch("activity_serve.core.ld.jsonld.compact")
def test_normalize_with_custom_context(mock_compact):
    """Test normalize with custom context."""
    mock_result = {"id": "test", "type": "Note", "name": "Test Note"}
    mock_compact.return_value = mock_result

    custom_context = {
        "@context": {"@vocab": "http://example.org/", "name": "http://schema.org/name"}
    }

    doc = {"id": "test", "type": "Note"}
    normalize(doc, context=custom_context)

    args = mock_compact.call_args[0]
    assert args[1] == custom_context


@patch("activity_serve.core.ld.jsonld.compact")
def test_normalize_with_compact_keys(mock_compact):
    """Test normalize with compact_keys parameter."""
    mock_result = {
        "id": "test",
        "type": ["Note"],
        "name": "Test Note",
        "attachment": [{"url": "test-url"}],
        "tag": ["tag1", "tag2"],
    }
    mock_compact.return_value = mock_result

    doc = {"id": "test", "type": "Note"}
    result = normalize(doc, compact_keys=["attachment", "tag"])

    assert result["type"] == ["Note"]
    assert result["attachment"] == {"url": "test-url"}
    assert result["tag"] == "tag1"
