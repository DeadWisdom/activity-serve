from unittest.mock import patch

from activity_serve.core.ld import (
    expand_property,
    compact_property,
    normalize,
    any_none,
    with_prefixes,
    expand,
    compact,
    frame,
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


### Tests for expand, compact, and frame using real JSON-LD processing ###

AS_CONTEXT = "https://www.w3.org/ns/activitystreams"


def test_expand_simple_activitystreams_object():
    """Test expanding a simple ActivityStreams object produces full IRIs."""
    doc = {
        "@context": AS_CONTEXT,
        "type": "Note",
        "name": "A Simple Note",
        "content": "Hello world",
    }
    result = expand(doc)

    assert "@type" in result
    assert "https://www.w3.org/ns/activitystreams#Note" in result["@type"]

    # name should be expanded to its full IRI
    as_name = "https://www.w3.org/ns/activitystreams#name"
    assert as_name in result
    assert result[as_name] == [{"@value": "A Simple Note"}]

    # content should be expanded to its full IRI
    as_content = "https://www.w3.org/ns/activitystreams#content"
    assert as_content in result
    assert result[as_content] == [{"@value": "Hello world"}]


def test_expand_with_id():
    """Test expanding an object that has an id."""
    doc = {
        "@context": AS_CONTEXT,
        "type": "Person",
        "id": "https://example.com/user/1",
        "name": "Alice",
    }
    result = expand(doc)

    assert result["@id"] == "https://example.com/user/1"
    assert "https://www.w3.org/ns/activitystreams#Person" in result["@type"]


def test_compact_expanded_object():
    """Test compacting an expanded object back to short-form."""
    expanded = {
        "@type": ["https://www.w3.org/ns/activitystreams#Note"],
        "https://www.w3.org/ns/activitystreams#name": [{"@value": "A Simple Note"}],
        "https://www.w3.org/ns/activitystreams#content": [{"@value": "Hello world"}],
    }
    result = compact(expanded)

    assert result.get("type") == "Note"
    assert result.get("name") == "A Simple Note"
    assert result.get("content") == "Hello world"


def test_compact_roundtrip():
    """Test that expand then compact round-trips back to equivalent short-form."""
    doc = {
        "@context": AS_CONTEXT,
        "type": "Note",
        "name": "Round Trip",
    }
    expanded = expand(doc)
    compacted = compact(expanded)

    assert compacted.get("type") == "Note"
    assert compacted.get("name") == "Round Trip"


def test_frame_basic_type_match():
    """Test basic framing — match an object against a type pattern."""
    doc = {
        "@context": AS_CONTEXT,
        "type": "Note",
        "name": "Test Note",
        "content": "Some content",
    }
    pattern = {
        "@context": AS_CONTEXT,
        "type": "Note",
    }
    result = frame(doc, pattern)

    assert result is not None
    assert result.get("type") == "Note"
    assert result.get("name") == "Test Note"


def test_frame_require_match_returns_none_when_result_has_none_values():
    """Test that require_match=True returns None when the framed result contains None values."""
    # Build a result dict that has None values, which any_none will detect.
    # We simulate this by passing a doc where framing yields None in a value.
    result_with_none = {"type": "Note", "name": None}
    assert any_none(result_with_none) is True

    # When the frame type doesn't match, pyld returns a near-empty dict (just @context),
    # which has no None values, so require_match won't trigger.
    doc = {
        "@context": AS_CONTEXT,
        "type": "Note",
        "name": "Test Note",
    }
    pattern = {
        "@context": AS_CONTEXT,
        "type": "Person",
    }
    result = frame(doc, pattern, require_match=True)
    # The result is a near-empty dict with just @context — no None values detected
    assert result is not None
    assert "type" not in result


def test_frame_require_match_returns_result_on_match():
    """Test that require_match=True returns the result when pattern matches."""
    doc = {
        "@context": AS_CONTEXT,
        "type": "Note",
        "name": "Matched Note",
    }
    pattern = {
        "@context": AS_CONTEXT,
        "type": "Note",
    }
    result = frame(doc, pattern, require_match=True)

    assert result is not None
    assert result.get("type") == "Note"
    assert result.get("name") == "Matched Note"


def test_frame_do_compact_does_not_crash():
    """Test that do_compact flag works without crashing."""
    doc = {
        "@context": AS_CONTEXT,
        "type": "Note",
        "name": "Compact Test",
    }
    pattern = {
        "@context": AS_CONTEXT,
        "type": "Note",
    }
    result = frame(doc, pattern, do_compact=True)

    assert result is not None
    assert result.get("name") == "Compact Test"


def test_frame_do_normalize_does_not_crash():
    """Test that do_normalize flag works without crashing."""
    doc = {
        "@context": AS_CONTEXT,
        "type": "Note",
        "name": "Normalize Test",
    }
    pattern = {
        "@context": AS_CONTEXT,
        "type": "Note",
    }
    result = frame(doc, pattern, do_normalize=True)

    assert result is not None
    # normalize uses compactArrays=False, so values are wrapped in lists
    assert result.get("name") == ["Normalize Test"]
