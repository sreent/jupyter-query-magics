"""cellspell.spells.mongodb — MongoDB cell magic powered by PyMongo.

Usage:
    %load_ext cellspell.mongodb    # Load only this spell
    %load_ext cellspell            # Or load all spells

Commands:
    %mongo_connect mongodb://localhost:27017/mydb   Connect to database
    %mongo_info                                     Show connection info

    %%mongodb collection_name                       find({}) on collection
    %%mongodb collection_name --op aggregate        Run an aggregation
    %%mongodb collection_name --limit 5             Limit results
"""

import json

from IPython.core.magic import Magics, cell_magic, line_magic, magics_class


def _check_pymongo():
    """Check if pymongo is available."""
    try:
        import pymongo  # noqa: F401

        return pymongo
    except ImportError:
        raise RuntimeError(
            "pymongo not found. Install it with:\n"
            "  pip install pymongo\n"
            "  pip install cellspell[mongodb]"
        )


def _parse_json_body(text):
    """Parse the cell body as JSON (filter, pipeline, or document).

    Supports both strict JSON and relaxed MongoDB-shell-style syntax
    by handling common differences (single quotes, unquoted keys are NOT
    handled — we require valid JSON).
    """
    text = text.strip()
    if not text:
        return {}

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in cell body: {e}")


def _format_documents(docs, limit=None):
    """Format MongoDB documents as pretty-printed JSON."""
    if not docs:
        return "(no results)"

    lines = []
    count = 0
    for doc in docs:
        if limit is not None and count >= limit:
            break
        # Convert ObjectId and other BSON types to strings
        lines.append(json.dumps(_serialize_doc(doc), indent=2, ensure_ascii=False))
        count += 1

    if not lines:
        return "(no results)"

    output = "\n---\n".join(lines)
    output += f"\n\n({count} document{'s' if count != 1 else ''})"
    return output


def _serialize_doc(obj):
    """Recursively convert BSON types to JSON-serializable types."""
    if isinstance(obj, dict):
        return {k: _serialize_doc(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_serialize_doc(item) for item in obj]
    elif hasattr(obj, "__str__") and type(obj).__name__ in (
        "ObjectId",
        "Decimal128",
        "Binary",
        "Regex",
        "Code",
        "DBRef",
    ):
        return str(obj)
    elif hasattr(obj, "isoformat"):
        # datetime
        return obj.isoformat()
    else:
        return obj


@magics_class
class MongoDBMagics(Magics):
    """Jupyter magics for running MongoDB queries via PyMongo."""

    _client = None
    _db = None
    _uri = None
    _db_name = None

    @line_magic
    def mongo_connect(self, line):
        """Connect to a MongoDB instance.

        Usage:
            %mongo_connect mongodb://localhost:27017/mydb
            %mongo_connect mongodb://localhost:27017 -d mydb
            %mongo_connect mongodb://user:pass@host:27017/mydb
        """
        pymongo = _check_pymongo()

        parts = line.strip().split()
        if not parts:
            if self._uri:
                print(f"Current connection: {self._uri}")
                print(f"Database: {self._db_name or '(none)'}")
            else:
                print("No connection. Usage: %mongo_connect mongodb://host:27017/mydb")
            return

        uri = parts[0]
        db_name = None

        i = 1
        while i < len(parts):
            if parts[i] in ("-d", "--database") and i + 1 < len(parts):
                db_name = parts[i + 1]
                i += 2
            else:
                print(f"Unknown option: {parts[i]}")
                return

        # Close existing connection
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass

        try:
            self._client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)

            # Extract database from URI if not specified via flag
            if db_name is None:
                parsed_db = self._client.get_default_database()
                if parsed_db is not None:
                    db_name = parsed_db.name

            if db_name:
                self._db = self._client[db_name]
                self._db_name = db_name
            else:
                self._db = None
                self._db_name = None

            # Verify connectivity
            self._client.admin.command("ping")

            self._uri = uri
            print(f"✓ Connected to {uri}")
            if db_name:
                print(f"  Database: {db_name}")
            else:
                print(
                    "  No database selected. "
                    "Use: %mongo_connect <uri> -d <dbname>"
                )
        except Exception as e:
            self._client = None
            self._db = None
            self._uri = None
            self._db_name = None
            print(f"Connection failed: {e}")

    @line_magic
    def mongo_info(self, line):
        """Show current MongoDB connection info."""
        _check_pymongo()
        if self._client is None:
            print("Not connected. Use %mongo_connect mongodb://host:27017/mydb")
            return

        print(f"URI:         {self._uri}")
        print(f"Database:    {self._db_name or '(none)'}")

        try:
            info = self._client.server_info()
            print(f"Server:      MongoDB {info.get('version', '?')}")
        except Exception as e:
            print(f"Server:      (unable to retrieve — {e})")

        if self._db is not None:
            try:
                collections = self._db.list_collection_names()
                if collections:
                    print(f"Collections: {', '.join(sorted(collections))}")
                else:
                    print("Collections: (none)")
            except Exception:
                pass

    @cell_magic
    def mongodb(self, line, cell):
        """Run a MongoDB query against a collection.

        Operations:
            find (default) — query documents
            aggregate      — run aggregation pipeline
            count          — count matching documents
            distinct       — get distinct values for a field

        Usage:
            %%mongodb users
            {"age": {"$gt": 25}}

            %%mongodb users --op aggregate
            [{"$group": {"_id": "$city", "n": {"$sum": 1}}}]

            %%mongodb users --op count
            {"active": true}

            %%mongodb users --op distinct --field city
            {"country": "US"}

            %%mongodb users --limit 5 --sort {"age": -1}
            {}
        """
        _check_pymongo()

        if self._db is None:
            print(
                "Error: No database selected.\n"
                "Use: %mongo_connect mongodb://host:27017/mydb"
            )
            return

        parts = line.strip().split()
        collection_name = None
        operation = "find"
        limit = 20
        sort_spec = None
        field = None

        i = 0
        while i < len(parts):
            if parts[i] in ("--op", "--operation") and i + 1 < len(parts):
                operation = parts[i + 1].lower()
                i += 2
            elif parts[i] == "--limit" and i + 1 < len(parts):
                try:
                    limit = int(parts[i + 1])
                except ValueError:
                    print(f"Invalid limit: {parts[i + 1]}")
                    return
                i += 2
            elif parts[i] == "--sort" and i + 1 < len(parts):
                try:
                    sort_spec = json.loads(parts[i + 1])
                except json.JSONDecodeError:
                    print(f"Invalid sort JSON: {parts[i + 1]}")
                    return
                i += 2
            elif parts[i] == "--field" and i + 1 < len(parts):
                field = parts[i + 1]
                i += 2
            elif not parts[i].startswith("--"):
                collection_name = parts[i]
                i += 1
            else:
                print(f"Unknown option: {parts[i]}")
                return

        if collection_name is None:
            print("Error: No collection specified. Usage: %%mongodb <collection>")
            return

        body = cell.strip()

        try:
            collection = self._db[collection_name]

            if operation == "find":
                query = _parse_json_body(body) if body else {}
                cursor = collection.find(query)
                if sort_spec:
                    cursor = cursor.sort(list(sort_spec.items()))
                cursor = cursor.limit(limit)
                docs = list(cursor)
                print(_format_documents(docs))

            elif operation == "aggregate":
                pipeline = _parse_json_body(body) if body else []
                if not isinstance(pipeline, list):
                    print("Error: Aggregation pipeline must be a JSON array.")
                    return
                docs = list(collection.aggregate(pipeline))
                print(_format_documents(docs, limit=limit))

            elif operation == "count":
                query = _parse_json_body(body) if body else {}
                count = collection.count_documents(query)
                print(f"{count}")

            elif operation == "distinct":
                if not field:
                    print("Error: --field required for distinct. "
                          "Usage: %%mongodb col --op distinct --field name")
                    return
                query = _parse_json_body(body) if body else {}
                values = collection.distinct(field, query)
                for v in values:
                    print(v)
                print(f"\n({len(values)} distinct value{'s' if len(values) != 1 else ''})")

            elif operation in ("insert", "insert_one"):
                doc = _parse_json_body(body)
                if isinstance(doc, list):
                    result = collection.insert_many(doc)
                    print(f"Inserted {len(result.inserted_ids)} document(s)")
                else:
                    result = collection.insert_one(doc)
                    print(f"Inserted: {result.inserted_id}")

            elif operation == "insert_many":
                docs = _parse_json_body(body)
                if not isinstance(docs, list):
                    print("Error: insert_many requires a JSON array.")
                    return
                result = collection.insert_many(docs)
                print(f"Inserted {len(result.inserted_ids)} document(s)")

            elif operation == "delete":
                query = _parse_json_body(body) if body else {}
                if not query:
                    print("Error: Empty filter for delete — use {\"_confirm\": true} to delete all.")
                    return
                result = collection.delete_many(query)
                print(f"Deleted {result.deleted_count} document(s)")

            else:
                print(
                    f"Unknown operation: {operation}\n"
                    "Supported: find, aggregate, count, distinct, insert, delete"
                )

        except ValueError as e:
            print(f"Parse error: {e}")
        except Exception as e:
            print(f"MongoDB error: {e}")


def load_ipython_extension(ipython):
    """Load the MongoDB spell.

    Usage: %load_ext cellspell.mongodb
    """
    _check_pymongo()
    ipython.register_magics(MongoDBMagics)
    print("✓ mongodb spell loaded — %mongo_connect, %mongo_info, %%mongodb")


def unload_ipython_extension(ipython):
    """Unload the MongoDB spell."""
    pass
