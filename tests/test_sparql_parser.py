"""Tests for SPARQL formatting and parsing functions."""

import pytest

from cellspell.spells.sparql import _format_table, _guess_rdf_format


class TestFormatTable:
    def test_empty_rows(self):
        assert _format_table(["a", "b"], []) == "(no results)"

    def test_single_row(self):
        result = _format_table(["name", "age"], [["Alice", "30"]])
        assert "name" in result
        assert "age" in result
        assert "Alice" in result
        assert "30" in result
        assert "(1 row)" in result

    def test_multiple_rows(self):
        result = _format_table(
            ["name", "age"],
            [["Alice", "30"], ["Bob", "25"]],
        )
        assert "Alice" in result
        assert "Bob" in result
        assert "(2 rows)" in result

    def test_column_alignment(self):
        result = _format_table(["x"], [["short"], ["a much longer value"]])
        lines = result.strip().split("\n")
        # Header is ljust-padded, separator uses dashes — same raw length
        assert len(lines[0]) == len(lines[1])

    def test_separator_format(self):
        result = _format_table(["a", "b"], [["1", "2"]])
        lines = result.strip().split("\n")
        assert "-+-" in lines[1]


class TestGuessRdfFormat:
    def test_turtle(self):
        assert _guess_rdf_format("data.ttl") == "turtle"

    def test_rdf_xml(self):
        assert _guess_rdf_format("data.rdf") == "xml"

    def test_owl(self):
        assert _guess_rdf_format("ontology.owl") == "xml"

    def test_n3(self):
        assert _guess_rdf_format("data.n3") == "n3"

    def test_ntriples(self):
        assert _guess_rdf_format("data.nt") == "nt"

    def test_jsonld(self):
        assert _guess_rdf_format("data.jsonld") == "json-ld"

    def test_trig(self):
        assert _guess_rdf_format("data.trig") == "trig"

    def test_nquads(self):
        assert _guess_rdf_format("data.nq") == "nquads"

    def test_unknown_defaults_to_turtle(self):
        assert _guess_rdf_format("data.xyz") == "turtle"

    def test_no_extension_defaults_to_turtle(self):
        assert _guess_rdf_format("datafile") == "turtle"

    def test_case_insensitive(self):
        assert _guess_rdf_format("data.TTL") == "turtle"
        assert _guess_rdf_format("data.RDF") == "xml"
