"""Tests for adaptive span name functionality through SpanPath."""

from huglog.output.rich import SpanName, TrimmingSpanNameTmpl
from huglog.output.rich.span import SpanPath


def render_span_path(spans: list, width: int, separator: str = ">") -> str:
    """Helper to render SpanPath using __format__ protocol."""
    span_path = SpanPath(span_messages=spans, separator=separator)
    return format(span_path, str(width))


def test_span_path_empty():
    """Empty span list renders as empty string."""
    rendered = render_span_path([], width=80)
    assert rendered == ""


def test_span_path_plain_strings():
    """Plain strings render and overflow without compression."""
    # Single plain string
    rendered = render_span_path(["process_request"], width=80)
    assert "> process_request" in rendered
    assert rendered.count(">") == 1

    # Multiple plain strings
    rendered = render_span_path(["span_one", "span_two", "span_three"], width=80)
    assert rendered.count(">") == 3
    assert all(name in rendered for name in ["span_one", "span_two", "span_three"])

    # Plain strings overflow when width is limited (no compression)
    spans = ["very_long_span_name_one", "very_long_span_name_two", "very_long_span_name_three"]
    rendered = render_span_path(spans, width=40)
    assert rendered.count(">") == 3
    assert len(rendered) > 40  # Overflow


def test_simple_trim_template_basic():
    """SimpleTrimSpanNameTmpl formats correctly."""
    tmpl = TrimmingSpanNameTmpl("processing {file} in {dir}")
    span = tmpl.format(file="test.py", dir="/home/user")

    assert isinstance(span, SpanName)
    assert isinstance(span, str)
    assert str(span) == "processing test.py in /home/user"


def test_simple_trim_template_compression():
    """SimpleTrimSpanNameTmpl compresses with middle ellipsis via format spec."""
    tmpl = TrimmingSpanNameTmpl("{msg}")
    span = tmpl.format(msg="this_is_a_very_long_message")

    compressed = f"{span:15}"
    assert len(compressed) == 15
    assert "..." in compressed


def test_simple_trim_template_in_spanpath():
    """TrimmingSpanNameTmpl works correctly in SpanPath rendering."""
    # Template with multiple placeholders - only keeps first one
    tmpl = TrimmingSpanNameTmpl("{operation} {file}")
    span = tmpl.format(operation="processing", file="verylongfilename.py")
    # Trimmed to "{operation}", formats to "processing"
    rendered = render_span_path([span], width=30)
    assert "processing" in rendered
    assert "verylongfilename" not in rendered  # Second placeholder dropped

    # Narrow width triggers compression
    tmpl = TrimmingSpanNameTmpl("{msg}")
    span = tmpl.format(msg="this_is_a_very_long_message_that_needs_compression")
    rendered = render_span_path([span], width=20)
    assert "..." in rendered

    # Template length determines width allocation
    tmpl = TrimmingSpanNameTmpl("{action}")
    span = tmpl.format(action="process_request")
    rendered = render_span_path([span, "other"], width=120)
    # len(span) = len("{action}") = 8, so width allocation is min(span_width, 8)
    assert "other" in rendered


def test_mixed_spans():
    """Plain strings and template spans can be mixed in SpanPath."""
    tmpl = TrimmingSpanNameTmpl("{handler}")
    span = tmpl.format(handler="long_request_handler")

    spans = ["plain", span, "another"]
    rendered = render_span_path(spans, width=60)

    assert rendered.count(">") == 3
    assert "plain" in rendered
    assert "another" in rendered


def test_formatting_methods():
    """SimpleTrimSpanNameTmpl supports both % and .format() syntax."""
    # .format() method
    tmpl = TrimmingSpanNameTmpl("processing {file}")
    span = tmpl.format(file="test.py")
    assert isinstance(span, SpanName)
    assert str(span) == "processing test.py"

    # % operator
    tmpl = TrimmingSpanNameTmpl("processing %(file)s")
    span = tmpl % {"file": "test.py"}
    assert isinstance(span, SpanName)
    assert str(span) == "processing test.py"


def test_span_name_behavior():
    """SpanName stores template, str() returns formatted value."""
    tmpl = TrimmingSpanNameTmpl("{name}")
    span = tmpl.format(name="test")

    assert isinstance(span, str)
    # SpanName stores the template as the str content
    assert span.upper() == "{NAME}"
    # Use str() to get the formatted value
    assert str(span) == "test"
    assert str(span).upper() == "TEST"


def test_custom_separator():
    """SpanPath custom separator works correctly."""
    spans = ["span1", "span2"]
    rendered = render_span_path(spans, width=80, separator="→")
    assert rendered.count("→") == 2
    assert "span1" in rendered
    assert "span2" in rendered


def test_span_path_format_edge_cases():
    """SpanPath __format__ handles edge cases correctly."""
    # Empty span list
    span_path = SpanPath(span_messages=[], separator=">")
    assert format(span_path, "100") == ""

    # Very narrow width - plain strings don't compress, they overflow
    span_path = SpanPath(span_messages=["span1", "span2"], separator=">")
    result = format(span_path, "5")
    assert "span1" in result
    assert "span2" in result
    # Plain strings overflow the width constraint

    # No width spec - returns str() representation
    span_path = SpanPath(span_messages=["span1", "span2"], separator=">")
    result = format(span_path, "")
    assert "span1" in result
    assert "span2" in result
