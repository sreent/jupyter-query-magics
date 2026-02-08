"""Tests for the mongosh syntax parser."""

import pytest

from cellspell.spells.mongodb import _parse_arg, _parse_mongosh, _split_args


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
