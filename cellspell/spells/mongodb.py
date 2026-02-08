"""cellspell.spells.mongodb — MongoDB cell magic powered by PyMongo.

Usage:
    %load_ext cellspell.mongodb    # Load only this spell
    %load_ext cellspell            # Or load all spells

Commands:
    %mongodb mongodb://localhost:27017/mydb   Connect to database
    %mongodb                                  Show connection info
    %%mongodb                                 Query using mongosh syntax
"""

import json

from IPython.core.magic import Magics, line_cell_magic, magics_class


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
        return obj.isoformat()
    else:
        return obj


def _print_documents(docs):
    """Format and print MongoDB documents as pretty-printed JSON."""
    if not docs:
        print("(no results)")
        return

    lines = []
    for doc in docs:
        lines.append(json.dumps(_serialize_doc(doc), indent=2, ensure_ascii=False))

    if not lines:
        print("(no results)")
        return

    count = len(lines)
    output = "\n---\n".join(lines)
    output += f"\n\n({count} document{'s' if count != 1 else ''})"
    print(output)


def _split_args(args_str):
    """Split comma-separated arguments respecting JSON nesting and strings."""
    args_str = args_str.strip()
    if not args_str:
        return []

    args = []
    depth = 0
    current = []
    in_string = False
    string_char = None
    escape = False

    for ch in args_str:
        if escape:
            current.append(ch)
            escape = False
            continue
        if ch == "\\":
            current.append(ch)
            escape = True
            continue
        if ch in ('"', "'"):
            if not in_string:
                in_string = True
                string_char = ch
            elif ch == string_char:
                in_string = False
            current.append(ch)
            continue
        if in_string:
            current.append(ch)
            continue
        if ch in ("{", "[", "("):
            depth += 1
            current.append(ch)
        elif ch in ("}", "]", ")"):
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(ch)

    if current:
        args.append("".join(current).strip())

    return args


def _parse_arg(arg_str):
    """Parse a single argument: JSON object/array, string, number, or boolean."""
    arg_str = arg_str.strip()
    if not arg_str:
        return None

    # Try JSON first (handles objects, arrays, strings, numbers, booleans, null)
    try:
        return json.loads(arg_str)
    except json.JSONDecodeError:
        pass

    # Try with single quotes replaced (basic mongosh compatibility)
    if "'" in arg_str:
        try:
            return json.loads(arg_str.replace("'", '"'))
        except json.JSONDecodeError:
            pass

    # Handle bare single-quoted strings
    if len(arg_str) >= 2 and arg_str[0] == "'" and arg_str[-1] == "'":
        return arg_str[1:-1]

    # Try number
    try:
        return int(arg_str)
    except ValueError:
        pass
    try:
        return float(arg_str)
    except ValueError:
        pass

    raise ValueError(f"Cannot parse argument: {arg_str}")


def _parse_mongosh(text):
    """Parse mongo shell syntax: db.collection.method(args).chain(args)

    Returns (collection_name, [(method_name, [parsed_args]), ...])
    """
    text = text.strip()
    if not text.startswith("db."):
        raise ValueError(
            "Query must start with 'db.'\n"
            'Example: db.users.find({"age": {"$gt": 25}})'
        )

    rest = text[3:]  # remove "db."

    # Find first opening parenthesis to locate boundary between collection and method
    try:
        first_paren = rest.index("(")
    except ValueError:
        raise ValueError("Missing method call. Expected db.collection.method(...)")

    prefix = rest[:first_paren]
    try:
        last_dot = prefix.rindex(".")
    except ValueError:
        raise ValueError("Missing method. Expected db.collection.method(...)")

    collection = prefix[:last_dot]
    rest = rest[last_dot + 1:]  # "find({...}).sort({...}).limit(5)"

    # Parse method chain
    chain = []
    while rest:
        rest = rest.strip()
        if not rest:
            break

        try:
            paren_pos = rest.index("(")
        except ValueError:
            break

        method_name = rest[:paren_pos].strip()
        rest = rest[paren_pos:]

        # Find matching closing paren
        depth = 0
        in_string = False
        string_char = None
        escape = False
        end = -1
        for i, ch in enumerate(rest):
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch in ('"', "'"):
                if not in_string:
                    in_string = True
                    string_char = ch
                elif ch == string_char:
                    in_string = False
                continue
            if in_string:
                continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = i
                    break

        if end == -1:
            raise ValueError(f"Unmatched parenthesis in: {rest[:60]}")

        args_str = rest[1:end]
        raw_args = _split_args(args_str)
        parsed_args = [_parse_arg(a) for a in raw_args if a]
        rest = rest[end + 1:]

        # Skip leading dot for next method in chain
        if rest.startswith("."):
            rest = rest[1:]

        chain.append((method_name, parsed_args))

    if not chain:
        raise ValueError("No method call found.")

    return collection, chain


@magics_class
class MongoDBMagics(Magics):
    """Jupyter magics for running MongoDB queries via PyMongo."""

    _client = None
    _db = None
    _uri = None
    _db_name = None

    def _connect(self, uri, db_name=None):
        """Connect to MongoDB."""
        pymongo = _check_pymongo()

        # Close existing connection
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass

        try:
            self._client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)

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

            self._client.admin.command("ping")

            self._uri = uri
            print(f"✓ Connected to {uri}")
            if db_name:
                print(f"  Database: {db_name}")
            else:
                print(
                    "  No database selected. "
                    "Use: %mongodb <uri> -d <dbname>"
                )
        except Exception as e:
            self._client = None
            self._db = None
            self._uri = None
            self._db_name = None
            print(f"Connection failed: {e}")

    @line_cell_magic
    def mongodb(self, line, cell=None):
        """Connect to MongoDB or run a query.

        Line magic — connect or show info:
            %mongodb mongodb://localhost:27017/mydb      Connect
            %mongodb mongodb://host:27017 -d mydb        Connect with explicit db
            %mongodb                                     Show connection info

        Cell magic — run query using mongosh syntax:
            %%mongodb
            db.users.find({"age": {"$gt": 25}}).sort({"age": -1}).limit(5)

            %%mongodb mongodb://localhost:27017/mydb
            db.users.aggregate([{"$group": {"_id": "$city"}}])
        """
        line = line.strip()

        # --- Line magic: %mongodb (connect or show info) ---
        if cell is None:
            if not line:
                self._show_info()
                return
            self._parse_and_connect(line)
            return

        # --- Cell magic: %%mongodb (run query) ---

        # Handle inline connection string on %%mongodb line
        if line.startswith("mongodb://") or line.startswith("mongodb+srv://"):
            self._parse_and_connect(line)
            if self._db is None:
                return
        elif line:
            print(f"Unknown option: {line}")
            return

        if self._db is None:
            print(
                "Error: No database selected.\n"
                "Use: %mongodb mongodb://host:27017/mydb\n"
                "  or: %%mongodb mongodb://host:27017/mydb"
            )
            return

        query = cell.strip()
        if not query:
            print("Error: No query provided.")
            return

        try:
            collection_name, chain = _parse_mongosh(query)
        except ValueError as e:
            print(f"Parse error: {e}")
            return

        try:
            collection = self._db[collection_name]
            method_name, args = chain[0]
            self._execute(collection, collection_name, method_name, args, chain[1:])
        except Exception as e:
            print(f"MongoDB error: {e}")

    def _show_info(self):
        """Show current MongoDB connection info."""
        if self._client is None:
            print("Not connected. Use %mongodb mongodb://host:27017/mydb")
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

    def _parse_and_connect(self, line):
        """Parse connection string with optional -d flag and connect."""
        parts = line.strip().split()
        if not parts:
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

        self._connect(uri, db_name)

    def _execute(self, collection, col_name, method, args, chain):
        """Execute a MongoDB method with optional cursor chain."""

        # --- Read operations ---
        if method == "find":
            filter_doc = args[0] if len(args) > 0 else {}
            projection = args[1] if len(args) > 1 else None
            cursor = collection.find(filter_doc, projection)
            cursor = self._apply_cursor_chain(cursor, chain)
            _print_documents(list(cursor))

        elif method == "findOne":
            filter_doc = args[0] if len(args) > 0 else {}
            projection = args[1] if len(args) > 1 else None
            doc = collection.find_one(filter_doc, projection)
            if doc:
                print(json.dumps(_serialize_doc(doc), indent=2, ensure_ascii=False))
            else:
                print("(no result)")

        elif method == "aggregate":
            pipeline = args[0] if len(args) > 0 else []
            if not isinstance(pipeline, list):
                print("Error: aggregate() requires an array pipeline.")
                return
            docs = list(collection.aggregate(pipeline))
            _print_documents(docs)

        elif method == "countDocuments":
            filter_doc = args[0] if len(args) > 0 else {}
            count = collection.count_documents(filter_doc)
            print(count)

        elif method == "estimatedDocumentCount":
            count = collection.estimated_document_count()
            print(count)

        elif method == "distinct":
            if len(args) < 1:
                print("Error: distinct() requires a field name.")
                return
            field = args[0]
            filter_doc = args[1] if len(args) > 1 else {}
            values = collection.distinct(field, filter_doc)
            for v in values:
                print(v)
            print(f"\n({len(values)} distinct value{'s' if len(values) != 1 else ''})")

        # --- Write operations ---
        elif method == "insertOne":
            if len(args) < 1:
                print("Error: insertOne() requires a document.")
                return
            result = collection.insert_one(args[0])
            print(f"Inserted: {result.inserted_id}")

        elif method == "insertMany":
            if len(args) < 1:
                print("Error: insertMany() requires an array of documents.")
                return
            docs = args[0]
            if not isinstance(docs, list):
                print("Error: insertMany() requires an array of documents.")
                return
            result = collection.insert_many(docs)
            print(f"Inserted {len(result.inserted_ids)} document(s)")

        elif method == "updateOne":
            if len(args) < 2:
                print("Error: updateOne(filter, update) requires two arguments.")
                return
            result = collection.update_one(args[0], args[1])
            print(f"Matched: {result.matched_count}, Modified: {result.modified_count}")

        elif method == "updateMany":
            if len(args) < 2:
                print("Error: updateMany(filter, update) requires two arguments.")
                return
            result = collection.update_many(args[0], args[1])
            print(f"Matched: {result.matched_count}, Modified: {result.modified_count}")

        elif method == "replaceOne":
            if len(args) < 2:
                print("Error: replaceOne(filter, replacement) requires two arguments.")
                return
            result = collection.replace_one(args[0], args[1])
            print(f"Matched: {result.matched_count}, Modified: {result.modified_count}")

        elif method == "deleteOne":
            if len(args) < 1:
                print("Error: deleteOne() requires a filter.")
                return
            result = collection.delete_one(args[0])
            print(f"Deleted {result.deleted_count} document(s)")

        elif method == "deleteMany":
            if len(args) < 1:
                print("Error: deleteMany() requires a filter.")
                return
            if not args[0]:
                print(
                    "Error: Empty filter for deleteMany — "
                    "pass a filter or use db.col.drop()"
                )
                return
            result = collection.delete_many(args[0])
            print(f"Deleted {result.deleted_count} document(s)")

        elif method == "drop":
            collection.drop()
            print(f"Dropped collection: {col_name}")

        else:
            print(
                f"Unsupported method: {method}\n"
                "Supported: find, findOne, aggregate, countDocuments, distinct,\n"
                "           insertOne, insertMany, updateOne, updateMany,\n"
                "           replaceOne, deleteOne, deleteMany, drop"
            )

    def _apply_cursor_chain(self, cursor, chain):
        """Apply chained cursor methods (.sort, .limit, .skip)."""
        for method_name, args in chain:
            if method_name == "sort":
                if len(args) > 0:
                    sort_spec = args[0]
                    if isinstance(sort_spec, dict):
                        cursor = cursor.sort(list(sort_spec.items()))
                    else:
                        cursor = cursor.sort(sort_spec)
            elif method_name == "limit":
                if len(args) > 0:
                    cursor = cursor.limit(int(args[0]))
            elif method_name == "skip":
                if len(args) > 0:
                    cursor = cursor.skip(int(args[0]))
            else:
                print(f"Warning: Unsupported cursor method: .{method_name}()")
        return cursor


def load_ipython_extension(ipython):
    """Load the MongoDB spell.

    Usage: %load_ext cellspell.mongodb
    """
    ipython.register_magics(MongoDBMagics)
    print("✓ mongodb spell loaded — %mongodb, %%mongodb")


def unload_ipython_extension(ipython):
    """Unload the MongoDB spell."""
    pass
