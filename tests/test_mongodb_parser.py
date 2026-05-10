"""Tests for the mongosh syntax parser."""

import re
from datetime import datetime, timezone

import pytest

from cellspell.spells.mongodb import (
    _js_to_json,
    _parse_arg,
    _parse_mongosh,
    _split_args,
    _split_statements,
)


# --- _split_args ---


class TestSplitArgs:
    def test_empty(self):
        assert _split_args("") == []

    def test_single_arg(self):
        assert _split_args('{"name": "Alice"}') == ['{"name": "Alice"}']

    def test_two_args(self):
        result = _split_args('{"age": 30}, {"name": 1}')
        assert result == ['{"age": 30}', '{"name": 1}']

    def test_nested_braces(self):
        result = _split_args('{"age": {"$gt": 25}}, {"name": 1}')
        assert result == ['{"age": {"$gt": 25}}', '{"name": 1}']

    def test_string_with_comma(self):
        result = _split_args('"hello, world", 42')
        assert result == ['"hello, world"', "42"]

    def test_single_quoted_string(self):
        result = _split_args("'city', {'active': true}")
        assert result == ["'city'", "{'active': true}"]

    def test_nested_array(self):
        result = _split_args('[{"$match": {"x": 1}}, {"$group": {"_id": "$y"}}]')
        assert result == ['[{"$match": {"x": 1}}, {"$group": {"_id": "$y"}}]']

    def test_escaped_quote(self):
        result = _split_args(r'"he said \"hi\"", 1')
        assert result == [r'"he said \"hi\""', "1"]


# --- _parse_arg ---


class TestParseArg:
    def test_json_object(self):
        assert _parse_arg('{"name": "Alice"}') == {"name": "Alice"}

    def test_json_array(self):
        assert _parse_arg("[1, 2, 3]") == [1, 2, 3]

    def test_json_string(self):
        assert _parse_arg('"hello"') == "hello"

    def test_json_number(self):
        assert _parse_arg("42") == 42

    def test_json_float(self):
        assert _parse_arg("3.14") == 3.14

    def test_json_boolean(self):
        assert _parse_arg("true") is True
        assert _parse_arg("false") is False

    def test_json_null(self):
        assert _parse_arg("null") is None

    def test_single_quoted_object(self):
        assert _parse_arg("{'name': 'Alice'}") == {"name": "Alice"}

    def test_bare_single_quoted_string(self):
        assert _parse_arg("'city'") == "city"

    def test_integer(self):
        assert _parse_arg("100") == 100

    def test_negative_number(self):
        assert _parse_arg("-1") == -1

    def test_empty_returns_none(self):
        assert _parse_arg("") is None

    def test_unparseable_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            _parse_arg("not_valid_anything")


# --- _parse_mongosh ---


class TestParseMongosh:
    def test_simple_find(self):
        col, chain = _parse_mongosh("db.users.find({})")
        assert col == "users"
        assert len(chain) == 1
        assert chain[0][0] == "find"
        assert chain[0][1] == [{}]

    def test_find_with_filter(self):
        col, chain = _parse_mongosh('db.users.find({"age": {"$gt": 25}})')
        assert col == "users"
        assert chain[0][0] == "find"
        assert chain[0][1] == [{"age": {"$gt": 25}}]

    def test_find_with_projection(self):
        col, chain = _parse_mongosh('db.users.find({}, {"name": 1, "_id": 0})')
        assert col == "users"
        assert chain[0][1] == [{}, {"name": 1, "_id": 0}]

    def test_find_empty_args(self):
        col, chain = _parse_mongosh("db.users.find()")
        assert col == "users"
        assert chain[0][0] == "find"
        assert chain[0][1] == []

    def test_method_chain(self):
        col, chain = _parse_mongosh('db.users.find({}).sort({"age": -1}).limit(5)')
        assert col == "users"
        assert len(chain) == 3
        assert chain[0] == ("find", [{}])
        assert chain[1] == ("sort", [{"age": -1}])
        assert chain[2] == ("limit", [5])

    def test_findOne(self):
        col, chain = _parse_mongosh('db.products.findOne({"sku": "ABC"})')
        assert col == "products"
        assert chain[0][0] == "findOne"

    def test_aggregate(self):
        col, chain = _parse_mongosh(
            'db.orders.aggregate([{"$group": {"_id": "$status", "count": {"$sum": 1}}}])'
        )
        assert col == "orders"
        assert chain[0][0] == "aggregate"
        assert isinstance(chain[0][1][0], list)

    def test_insertOne(self):
        col, chain = _parse_mongosh('db.users.insertOne({"name": "Charlie", "age": 35})')
        assert col == "users"
        assert chain[0][0] == "insertOne"
        assert chain[0][1] == [{"name": "Charlie", "age": 35}]

    def test_deleteMany(self):
        col, chain = _parse_mongosh("db.logs.deleteMany({})")
        assert col == "logs"
        assert chain[0][0] == "deleteMany"
        assert chain[0][1] == [{}]

    def test_countDocuments(self):
        col, chain = _parse_mongosh('db.users.countDocuments({"active": true})')
        assert col == "users"
        assert chain[0][0] == "countDocuments"
        assert chain[0][1] == [{"active": True}]

    def test_distinct(self):
        col, chain = _parse_mongosh('db.users.distinct("city")')
        assert col == "users"
        assert chain[0][0] == "distinct"
        assert chain[0][1] == ["city"]

    def test_dotted_collection_name(self):
        col, chain = _parse_mongosh("db.system.profile.find({})")
        assert col == "system.profile"
        assert chain[0][0] == "find"

    def test_drop(self):
        col, chain = _parse_mongosh("db.temp.drop()")
        assert col == "temp"
        assert chain[0][0] == "drop"
        assert chain[0][1] == []

    def test_updateOne(self):
        col, chain = _parse_mongosh(
            'db.users.updateOne({"name": "Alice"}, {"$set": {"age": 31}})'
        )
        assert col == "users"
        assert chain[0][0] == "updateOne"
        assert chain[0][1] == [{"name": "Alice"}, {"$set": {"age": 31}}]

    def test_no_db_prefix_raises(self):
        with pytest.raises(ValueError, match="must start with 'db.'"):
            _parse_mongosh("users.find({})")

    def test_no_method_raises(self):
        with pytest.raises(ValueError, match="Missing method"):
            _parse_mongosh("db.users")

    def test_unmatched_paren_raises(self):
        with pytest.raises(ValueError, match="Unmatched parenthesis"):
            _parse_mongosh("db.users.find({")

    def test_multiline_query(self):
        query = """db.users.find(
            {"age": {"$gt": 25}},
            {"name": 1}
        ).sort({"name": 1}).limit(10)"""
        col, chain = _parse_mongosh(query)
        assert col == "users"
        assert len(chain) == 3
        assert chain[0][1] == [{"age": {"$gt": 25}}, {"name": 1}]

    def test_single_quoted_mongosh(self):
        col, chain = _parse_mongosh("db.users.find({'name': 'Alice'})")
        assert col == "users"
        assert chain[0][1] == [{"name": "Alice"}]

    def test_createIndex(self):
        col, chain = _parse_mongosh('db.users.createIndex({"email": 1})')
        assert col == "users"
        assert chain[0][0] == "createIndex"
        assert chain[0][1] == [{"email": 1}]

    def test_createIndex_with_options(self):
        col, chain = _parse_mongosh(
            'db.users.createIndex({"email": 1}, {"unique": true})'
        )
        assert col == "users"
        assert chain[0][0] == "createIndex"
        assert chain[0][1] == [{"email": 1}, {"unique": True}]

    def test_createCollection_db_level(self):
        col, chain = _parse_mongosh('db.createCollection("logs")')
        assert col is None
        assert chain[0][0] == "createCollection"
        assert chain[0][1] == ["logs"]

    def test_find_with_explain(self):
        col, chain = _parse_mongosh("db.users.find({}).explain()")
        assert col == "users"
        assert len(chain) == 2
        assert chain[0][0] == "find"
        assert chain[1][0] == "explain"

    def test_find_with_explain_verbosity(self):
        col, chain = _parse_mongosh('db.users.find({}).explain("executionStats")')
        assert col == "users"
        assert chain[1][0] == "explain"
        assert chain[1][1] == ["executionStats"]

    def test_aggregate_with_explain(self):
        col, chain = _parse_mongosh(
            'db.orders.aggregate([{"$group": {"_id": "$status"}}]).explain()'
        )
        assert col == "orders"
        assert chain[0][0] == "aggregate"
        assert chain[1][0] == "explain"


# --- _split_statements ---


class TestSplitStatements:
    def test_single_statement(self):
        assert _split_statements("db.users.find({})") == ["db.users.find({})"]

    def test_two_statements_newline(self):
        result = _split_statements("db.col.drop()\ndb.col.insertOne({})")
        assert result == ["db.col.drop()", "db.col.insertOne({})"]

    def test_two_statements_semicolon(self):
        result = _split_statements("db.col.drop(); db.col.insertOne({})")
        assert result == ["db.col.drop()", "db.col.insertOne({})"]

    def test_multiline_single_statement(self):
        query = """db.people.insertMany([
          {"_id": 1, "name": "Tom"},
          {"_id": 2, "name": "Jane"}
        ])"""
        result = _split_statements(query)
        assert len(result) == 1
        assert result[0].startswith("db.people.insertMany(")

    def test_drop_then_insertMany_multiline(self):
        query = """db.people.drop()
db.people.insertMany([
  {"_id": 1, "name": "Tom"},
  {"_id": 2, "name": "Jane"}
])"""
        result = _split_statements(query)
        assert len(result) == 2
        assert result[0] == "db.people.drop()"
        assert result[1].startswith("db.people.insertMany(")

    def test_trailing_semicolons(self):
        result = _split_statements("db.col.drop();\ndb.col.find();")
        assert result == ["db.col.drop()", "db.col.find()"]

    def test_empty_input(self):
        assert _split_statements("") == []
        assert _split_statements("   ") == []

    def test_three_statements(self):
        query = "db.a.drop()\ndb.a.insertOne({})\ndb.a.find({})"
        result = _split_statements(query)
        assert len(result) == 3

    def test_statement_with_dates(self):
        query = '''db.col.drop()
db.col.insertMany([{"d": new Date("2012-05-19")}])'''
        result = _split_statements(query)
        assert len(result) == 2

    def test_find_with_count_chain(self):
        query = 'db.users.find({"role": "passenger"}).count()'
        result = _split_statements(query)
        assert len(result) == 1
        assert result[0] == query

    def test_find_with_count_chain_multiline(self):
        query = 'db.users.find({"role": "passenger"})\n  .count()'
        result = _split_statements(query)
        assert len(result) == 1

    def test_find_with_explain_chain(self):
        query = 'db.users.find({"role": "driver"}).explain("executionStats")'
        result = _split_statements(query)
        assert len(result) == 1
        assert result[0] == query

    def test_find_with_sort_limit_chain(self):
        query = 'db.users.find({}).sort({"age": -1}).limit(10)'
        result = _split_statements(query)
        assert len(result) == 1
        assert result[0] == query

    def test_chained_then_new_statement(self):
        query = 'db.users.find({}).count()\ndb.orders.find({})'
        result = _split_statements(query)
        assert len(result) == 2
        assert result[0] == 'db.users.find({}).count()'
        assert result[1] == 'db.orders.find({})'

    def test_chained_then_new_statement_semicolon(self):
        query = 'db.users.find({}).count(); db.orders.find({})'
        result = _split_statements(query)
        assert len(result) == 2


# --- Mongosh JS constructor support (new Date, ObjectId, etc.) ---


class TestParseArgMongoshTypes:
    def test_new_date_string(self):
        result = _parse_arg('new Date("2012-05-19")')
        assert result == datetime(2012, 5, 19)

    def test_new_date_iso(self):
        result = _parse_arg('new Date("2024-01-15T10:30:00")')
        assert result == datetime(2024, 1, 15, 10, 30, 0)

    def test_new_date_iso_z(self):
        result = _parse_arg('new Date("2024-01-15T10:30:00Z")')
        assert result == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    def test_isodate(self):
        result = _parse_arg('ISODate("2023-06-01")')
        assert result == datetime(2023, 6, 1)

    def test_new_date_epoch_millis(self):
        result = _parse_arg("new Date(0)")
        assert result == datetime(1970, 1, 1, tzinfo=timezone.utc)

    def test_new_date_no_args(self):
        result = _parse_arg("new Date()")
        assert isinstance(result, datetime)

    def test_new_date_single_quotes(self):
        result = _parse_arg("new Date('2012-11-01')")
        assert result == datetime(2012, 11, 1)

    def test_object_with_date(self):
        result = _parse_arg('{"date_founded": new Date("2012-05-19")}')
        assert result == {"date_founded": datetime(2012, 5, 19)}

    def test_array_with_dates(self):
        result = _parse_arg(
            '[{"d": new Date("2012-05-19")}, {"d": new Date("2019-03-15")}]'
        )
        assert result == [
            {"d": datetime(2012, 5, 19)},
            {"d": datetime(2019, 3, 15)},
        ]


class TestParseMongoshWithDates:
    def test_insertOne_with_date(self):
        col, chain = _parse_mongosh(
            'db.events.insertOne({"name": "launch", "date": new Date("2024-01-01")})'
        )
        assert col == "events"
        assert chain[0][0] == "insertOne"
        doc = chain[0][1][0]
        assert doc["date"] == datetime(2024, 1, 1)

    def test_insertMany_with_dates(self):
        query = """db.people.insertMany([
          {"_id": 1, "businesses": [{"name": "Acme", "date_founded": new Date("2012-05-19")}]},
          {"_id": 2, "businesses": [{"name": "Corp", "date_founded": new Date("2019-03-15")}]}
        ])"""
        col, chain = _parse_mongosh(query)
        assert col == "people"
        assert chain[0][0] == "insertMany"
        docs = chain[0][1][0]
        assert docs[0]["businesses"][0]["date_founded"] == datetime(2012, 5, 19)
        assert docs[1]["businesses"][0]["date_founded"] == datetime(2019, 3, 15)

    def test_find_with_date_filter(self):
        col, chain = _parse_mongosh(
            'db.events.find({"date": {"$gte": new Date("2024-01-01")}})'
        )
        assert col == "events"
        assert chain[0][1][0]["date"]["$gte"] == datetime(2024, 1, 1)

    def test_isodate_in_query(self):
        col, chain = _parse_mongosh(
            'db.logs.find({"ts": ISODate("2023-06-01T00:00:00Z")})'
        )
        assert col == "logs"
        assert chain[0][1][0]["ts"] == datetime(
            2023, 6, 1, 0, 0, 0, tzinfo=timezone.utc
        )


# --- Regex support ---


class TestParseArgRegex:
    def test_regexp_constructor(self):
        result = _parse_arg('RegExp("^hello")')
        assert result.pattern == "^hello"
        assert result.flags & re.IGNORECASE == 0

    def test_regexp_constructor_with_flags(self):
        result = _parse_arg('RegExp("^hello", "i")')
        assert result.pattern == "^hello"
        assert result.flags & re.IGNORECASE

    def test_new_regexp_constructor(self):
        result = _parse_arg('new RegExp("^hello", "im")')
        assert result.pattern == "^hello"
        assert result.flags & re.IGNORECASE
        assert result.flags & re.MULTILINE

    def test_regexp_single_quotes(self):
        result = _parse_arg("RegExp('^hello', 'i')")
        assert result.pattern == "^hello"
        assert result.flags & re.IGNORECASE

    def test_object_with_regexp(self):
        result = _parse_arg('{"name": RegExp("^Al", "i")}')
        assert result["name"].pattern == "^Al"
        assert result["name"].flags & re.IGNORECASE

    def test_regex_literal(self):
        result = _parse_arg("{name: /^Al/i}")
        assert result["name"].pattern == "^Al"
        assert result["name"].flags & re.IGNORECASE

    def test_regex_literal_no_flags(self):
        result = _parse_arg("{name: /^Al/}")
        assert result["name"].pattern == "^Al"
        assert result["name"].flags & re.IGNORECASE == 0

    def test_regex_literal_multiple_flags(self):
        result = _parse_arg("{name: /^Al/im}")
        assert result["name"].pattern == "^Al"
        assert result["name"].flags & re.IGNORECASE
        assert result["name"].flags & re.MULTILINE

    def test_regex_with_escaped_slash(self):
        result = _parse_arg(r"{path: /^\/api\/users/}")
        assert result["path"].pattern == "^/api/users"

    def test_regex_in_array(self):
        result = _parse_arg('{"$in": [/^Al/i, /^Bo/]}')
        assert len(result["$in"]) == 2
        assert result["$in"][0].pattern == "^Al"
        assert result["$in"][1].pattern == "^Bo"


class TestParseMongoshWithRegex:
    def test_find_with_regex_literal(self):
        col, chain = _parse_mongosh("db.users.find({name: /^Al/i})")
        assert col == "users"
        assert chain[0][1][0]["name"].pattern == "^Al"
        assert chain[0][1][0]["name"].flags & re.IGNORECASE

    def test_find_with_regexp_constructor(self):
        col, chain = _parse_mongosh(
            'db.users.find({"name": RegExp("^Al", "i")})'
        )
        assert col == "users"
        assert chain[0][1][0]["name"].pattern == "^Al"

    def test_find_regex_in_dollar_in(self):
        col, chain = _parse_mongosh(
            'db.users.find({name: {"$in": [/^Al/i, /^Bo/]}})'
        )
        assert col == "users"
        patterns = chain[0][1][0]["name"]["$in"]
        assert patterns[0].pattern == "^Al"
        assert patterns[1].pattern == "^Bo"

    def test_regex_with_comment_on_same_line(self):
        col, chain = _parse_mongosh(
            "db.users.find({name: /^Al/i}) // find users"
        )
        assert col == "users"
        assert chain[0][1][0]["name"].pattern == "^Al"

    def test_regex_does_not_break_comments(self):
        query = """db.users.find(
            {name: /^Al/i}  // regex filter
        )"""
        col, chain = _parse_mongosh(query)
        assert col == "users"
        assert chain[0][1][0]["name"].pattern == "^Al"


# --- _js_to_json ---


class TestJsToJson:
    def test_unquoted_keys(self):
        assert _js_to_json("{name: 1}") == '{"name": 1}'

    def test_unquoted_dollar_operator(self):
        assert _js_to_json("{$lt: 20}") == '{"$lt": 20}'

    def test_nested_unquoted(self):
        result = _js_to_json("{quantity: {$lt: 20}}")
        assert result == '{"quantity": {"$lt": 20}}'

    def test_mixed_quoted_unquoted(self):
        result = _js_to_json('{quantity: {$lt: 20}, "name": "Alice"}')
        assert result == '{"quantity": {"$lt": 20}, "name": "Alice"}'

    def test_single_quoted_strings(self):
        result = _js_to_json("{'name': 'Alice'}")
        assert result == '{"name": "Alice"}'

    def test_already_valid_json(self):
        text = '{"name": "Alice", "age": 30}'
        assert _js_to_json(text) == text

    def test_boolean_values_not_quoted(self):
        result = _js_to_json("{active: true}")
        assert result == '{"active": true}'

    def test_null_value_not_quoted(self):
        result = _js_to_json("{field: null}")
        assert result == '{"field": null}'

    def test_dollar_set_with_nested(self):
        result = _js_to_json('{$set: {status: "low"}}')
        assert result == '{"$set": {"status": "low"}}'

    def test_double_quote_inside_single_quoted_string(self):
        result = _js_to_json("""{'say': 'he said "hi"'}""")
        assert result == '{"say": "he said \\"hi\\""}'

    def test_single_line_comment(self):
        result = _js_to_json('{ likes: "fashun" } // find docs')
        import json

        assert json.loads(result) == {"likes": "fashun"}

    def test_block_comment(self):
        result = _js_to_json("{ /* filter */ likes: /* field */ \"fashun\" }")
        import json

        assert json.loads(result) == {"likes": "fashun"}

    def test_multiline_with_comments(self):
        text = """\
{ likes: "fashun" },           // first arg
{ $set: { "likes.$": "fashion" } }  // second arg"""
        result = _js_to_json(text)
        # Comments stripped, content preserved
        assert "// first arg" not in result
        assert "// second arg" not in result
        assert '"likes"' in result
        assert '"$set"' in result

    def test_comment_inside_string_not_stripped(self):
        result = _js_to_json('{ msg: "hello // world" }')
        import json

        assert json.loads(result) == {"msg": "hello // world"}

    def test_trailing_comma_in_array(self):
        import json

        assert json.loads(_js_to_json("[1, 2, 3,]")) == [1, 2, 3]

    def test_trailing_comma_in_object(self):
        import json

        assert json.loads(_js_to_json('{"a": 1, "b": 2,}')) == {"a": 1, "b": 2}

    def test_trailing_comma_with_newline_before_bracket(self):
        import json

        text = '[\n  "a",\n  "b",\n]'
        assert json.loads(_js_to_json(text)) == ["a", "b"]

    def test_trailing_comma_with_comment_before_bracket(self):
        import json

        text = '[\n  "a",\n  "b", // last\n]'
        assert json.loads(_js_to_json(text)) == ["a", "b"]

    def test_trailing_comma_inside_string_preserved(self):
        import json

        assert json.loads(_js_to_json('"a, b,"')) == "a, b,"

    def test_non_trailing_comma_kept(self):
        import json

        assert json.loads(_js_to_json("[1, 2, 3]")) == [1, 2, 3]


class TestParseArgTrailingCommas:
    def test_array_trailing_comma(self):
        assert _parse_arg("[1, 2, 3,]") == [1, 2, 3]

    def test_object_trailing_comma(self):
        assert _parse_arg('{"a": 1, "b": 2,}') == {"a": 1, "b": 2}

    def test_nested_arrays_trailing_commas(self):
        result = _parse_arg(
            '{"genre": ["Action", "Sci-Fi",], "actors": ["A", "B",]}'
        )
        assert result == {"genre": ["Action", "Sci-Fi"], "actors": ["A", "B"]}

    def test_star_trek_film_doc(self):
        # The exact shape the user pasted: trailing commas in nested arrays
        # plus ISODate(...) constructors plus mixed booleans.
        text = '''{
            "title": "Star Trek Into Darkness",
            "year": 2013,
            "genre": [
                "Action",
                "Adventure",
                "Sci-Fi",
            ],
            "actors": [
                "Pine, Chris",
                "Quinto, Zachary",
                "Saldana, Zoe",
            ],
            "releases": [
                {
                    "country": "USA",
                    "date": ISODate("2013-05-17"),
                    "prerelease": true
                },
                {
                    "country": "Germany",
                    "date": ISODate("2013-05-16"),
                    "prerelease": false
                }
            ]
        }'''
        doc = _parse_arg(text)
        assert doc["title"] == "Star Trek Into Darkness"
        assert doc["year"] == 2013
        assert doc["genre"] == ["Action", "Adventure", "Sci-Fi"]
        assert doc["actors"] == ["Pine, Chris", "Quinto, Zachary", "Saldana, Zoe"]
        assert len(doc["releases"]) == 2
        assert doc["releases"][0]["country"] == "USA"
        assert doc["releases"][0]["date"] == datetime(2013, 5, 17)
        assert doc["releases"][0]["prerelease"] is True
        assert doc["releases"][1]["prerelease"] is False


class TestInsertAlias:
    """db.coll.insert(...) is the legacy mongosh alias for insertOne/insertMany."""

    def test_insert_single_doc_parses(self):
        col, chain = _parse_mongosh('db.films.insert({"title": "Andor"})')
        assert col == "films"
        assert chain[0][0] == "insert"
        assert chain[0][1] == [{"title": "Andor"}]

    def test_insert_array_parses(self):
        col, chain = _parse_mongosh(
            'db.films.insert([{"title": "A"}, {"title": "B"}])'
        )
        assert col == "films"
        assert chain[0][0] == "insert"
        assert chain[0][1] == [[{"title": "A"}, {"title": "B"}]]

    def test_insert_with_trailing_commas_and_isodate(self):
        col, chain = _parse_mongosh(
            'db.films.insert({"title": "X", "tags": ["a", "b",], '
            '"date": ISODate("2013-05-17"),})'
        )
        assert col == "films"
        assert chain[0][0] == "insert"
        doc = chain[0][1][0]
        assert doc["tags"] == ["a", "b"]
        assert doc["date"] == datetime(2013, 5, 17)


# --- Unquoted mongosh syntax (end-to-end) ---


class TestUnquotedMongoshSyntax:
    def test_find_unquoted_keys(self):
        col, chain = _parse_mongosh("db.inventory.find({quantity: {$lt: 20}})")
        assert col == "inventory"
        assert chain[0][0] == "find"
        assert chain[0][1] == [{"quantity": {"$lt": 20}}]

    def test_find_unquoted_with_projection(self):
        col, chain = _parse_mongosh(
            "db.inventory.find({quantity: {$lt: 20}}, {name: 1, _id: 0})"
        )
        assert col == "inventory"
        assert chain[0][1] == [{"quantity": {"$lt": 20}}, {"name": 1, "_id": 0}]

    def test_updateMany_unquoted(self):
        col, chain = _parse_mongosh(
            'db.inventory.updateMany({quantity: {$lt: 20}}, {$set: {status: "low"}})'
        )
        assert col == "inventory"
        assert chain[0][0] == "updateMany"
        assert chain[0][1] == [
            {"quantity": {"$lt": 20}},
            {"$set": {"status": "low"}},
        ]

    def test_updateOne_unquoted(self):
        col, chain = _parse_mongosh(
            'db.users.updateOne({name: "Alice"}, {$set: {age: 31}})'
        )
        assert col == "users"
        assert chain[0][0] == "updateOne"
        assert chain[0][1] == [{"name": "Alice"}, {"$set": {"age": 31}}]

    def test_find_unquoted_gte(self):
        col, chain = _parse_mongosh("db.users.find({age: {$gte: 18}})")
        assert col == "users"
        assert chain[0][1] == [{"age": {"$gte": 18}}]

    def test_aggregate_unquoted(self):
        col, chain = _parse_mongosh(
            'db.orders.aggregate([{$group: {_id: "$status", count: {$sum: 1}}}])'
        )
        assert col == "orders"
        assert chain[0][0] == "aggregate"
        pipeline = chain[0][1][0]
        assert pipeline == [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]

    def test_deleteMany_unquoted(self):
        col, chain = _parse_mongosh("db.logs.deleteMany({level: \"debug\"})")
        assert col == "logs"
        assert chain[0][0] == "deleteMany"
        assert chain[0][1] == [{"level": "debug"}]

    def test_insertOne_unquoted(self):
        col, chain = _parse_mongosh(
            'db.users.insertOne({name: "Bob", age: 25, active: true})'
        )
        assert col == "users"
        assert chain[0][0] == "insertOne"
        assert chain[0][1] == [{"name": "Bob", "age": 25, "active": True}]

    def test_updateMany_with_comments_and_positional_operator(self):
        query = """db.people.updateMany(
            { likes: "fashun" },           // Find documents with "fashun" in likes
            { $set: { "likes.$": "fashion" } }  // Replace the matched element
        )"""
        col, chain = _parse_mongosh(query)
        assert col == "people"
        assert chain[0][0] == "updateMany"
        assert chain[0][1] == [
            {"likes": "fashun"},
            {"$set": {"likes.$": "fashion"}},
        ]

    def test_updateMany_with_block_comments(self):
        query = """db.people.updateMany(
            { /* filter */ likes: "fashun" },
            { $set: { "likes.$": "fashion" } }
        )"""
        col, chain = _parse_mongosh(query)
        assert col == "people"
        assert chain[0][0] == "updateMany"
        assert chain[0][1] == [
            {"likes": "fashun"},
            {"$set": {"likes.$": "fashion"}},
        ]


class TestCountParsing:
    """Tests for .count() parsing support."""

    def test_count_standalone(self):
        col, chain = _parse_mongosh('db.users.count()')
        assert col == "users"
        assert chain[0][0] == "count"
        assert chain[0][1] == []

    def test_count_with_filter(self):
        col, chain = _parse_mongosh('db.users.count({"age": {"$gt": 25}})')
        assert col == "users"
        assert chain[0][0] == "count"
        assert chain[0][1] == [{"age": {"$gt": 25}}]

    def test_find_count_chain(self):
        col, chain = _parse_mongosh('db.users.find({"active": true}).count()')
        assert col == "users"
        assert chain[0][0] == "find"
        assert chain[0][1] == [{"active": True}]
        assert chain[1][0] == "count"

    def test_find_count_chain_no_filter(self):
        col, chain = _parse_mongosh('db.orders.find().count()')
        assert col == "orders"
        assert chain[0][0] == "find"
        assert chain[1][0] == "count"


class TestPrettyChain:
    def test_find_pretty_parses(self):
        col, chain = _parse_mongosh('db.films.find().pretty()')
        assert col == "films"
        assert chain[0][0] == "find"
        assert chain[1][0] == "pretty"
        assert chain[1][1] == []

    def test_find_filter_then_pretty(self):
        col, chain = _parse_mongosh('db.films.find({"year": 2013}).pretty()')
        assert col == "films"
        assert chain[0][1] == [{"year": 2013}]
        assert chain[1][0] == "pretty"

    def test_apply_cursor_chain_pretty_is_noop(self):
        from cellspell.spells.mongodb import MongoDBMagics

        magics = MongoDBMagics.__new__(MongoDBMagics)

        class FakeCursor:
            sorted = False
            def sort(self, _):
                self.sorted = True
                return self

        cursor = FakeCursor()
        # Should not print or raise — pretty is silently consumed.
        result = magics._apply_cursor_chain(cursor, [("pretty", [])])
        assert result is cursor
