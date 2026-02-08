"""Tests for XPath helper functions."""

import shutil

import pytest

from cellspell.spells.xpath import _format_xml


@pytest.mark.skipif(
    shutil.which("xmllint") is None,
    reason="xmllint not installed",
)
class TestFormatXml:
    def test_simple_element(self):
        result = _format_xml("<book><title>Test</title></book>")
        assert "<book>" in result
        assert "<title>Test</title>" in result

    def test_preserves_content(self):
        result = _format_xml("<a>hello</a>")
        assert "hello" in result

    def test_removes_wrapper(self):
        result = _format_xml("<a>1</a><b>2</b>")
        assert "<wrapper>" not in result
        assert "</wrapper>" not in result

    def test_removes_xml_declaration(self):
        result = _format_xml("<root><item>x</item></root>")
        assert "<?xml" not in result

    def test_invalid_xml_returns_original(self):
        original = "not xml at all <<<"
        result = _format_xml(original)
        assert result == original
