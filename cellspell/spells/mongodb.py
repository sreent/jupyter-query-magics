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
import re
from datetime import datetime, timezone

from IPython.core.magic import Magics, line_cell_magic, magics_class


# ---------------------------------------------------------------------------
# Mongosh JavaScript constructor preprocessing
# ---------------------------------------------------------------------------
# Sentinel prefix used in placeholder strings so they survive JSON parsing
# and can be resolved to Python types afterward.
_MONGOSH_SENTINEL = "__mongosh_type__"

_RE_DATE_STRING = re.compile(
    r"""(?:new\s+Date|ISODate)\s*\(\s*["']([^"']*)["']\s*\)"""
)
_RE_DATE_NUMBER = re.compile(r"""new\s+Date\s*\(\s*(\d+)\s*\)""")
_RE_DATE_NOW = re.compile(r"""new\s+Date\s*\(\s*\)""")
_RE_OBJECTID = re.compile(
    r"""(?:new\s+)?ObjectId\s*\(\s*["']([0-9a-fA-F]{24})["']\s*\)"""
)
_RE_REGEXP = re.compile(
    r"""(?:new\s+)?RegExp\s*\(\s*["']([^"']*)["']\s*(?:,\s*["']([^"']*)["'])?\s*\)"""
)

# Map JavaScript regex flags to Python re module flags.
_JS_REGEX_FLAGS = {
    "i": re.IGNORECASE,
    "m": re.MULTILINE,
    "s": re.DOTALL,
    "x": re.VERBOSE,
}


def _preprocess_mongosh_extensions(text):
    """Replace mongosh JS constructors with JSON-compatible placeholder strings.

    Handles:
        new Date("..."), ISODate("..."), new Date(), new Date(millis),
        ObjectId("..."), new ObjectId("..."),
        RegExp("..."), RegExp("...", "flags"), new RegExp("...", "flags").
    """
    text = _RE_DATE_STRING.sub(
        lambda m: json.dumps(f"{_MONGOSH_SENTINEL}date:{m.group(1)}"), text
    )
    text = _RE_DATE_NUMBER.sub(
        lambda m: json.dumps(f"{_MONGOSH_SENTINEL}date_ms:{m.group(1)}"), text
    )
    text = _RE_DATE_NOW.sub(json.dumps(f"{_MONGOSH_SENTINEL}date_now"), text)
    text = _RE_OBJECTID.sub(
        lambda m: json.dumps(f"{_MONGOSH_SENTINEL}oid:{m.group(1)}"), text
    )
    text = _RE_REGEXP.sub(
        lambda m: json.dumps(
            f"{_MONGOSH_SENTINEL}regex:{m.group(2) or ''}:{m.group(1)}"
        ),
        text,
    )
    return text


def _resolve_mongosh_types(obj):
    """Recursively resolve mongosh type placeholders to Python/BSON types."""
    if isinstance(obj, str) and obj.startswith(_MONGOSH_SENTINEL):
        tag = obj[len(_MONGOSH_SENTINEL) :]
        if tag.startswith("date:"):
            date_str = tag[5:]
            if date_str.endswith("Z"):
                date_str = date_str[:-1] + "+00:00"
            return datetime.fromisoformat(date_str)
        elif tag == "date_now":
            return datetime.now(timezone.utc)
        elif tag.startswith("date_ms:"):
            ms = int(tag[8:])
            return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        elif tag.startswith("oid:"):
            oid_hex = tag[4:]
            try:
                from bson import ObjectId

                return ObjectId(oid_hex)
            except ImportError:
                return oid_hex
        elif tag.startswith("regex:"):
            rest = tag[6:]
            colon_idx = rest.index(":")
            flags_str = rest[:colon_idx]
            pattern = rest[colon_idx + 1 :]
            flags = 0
            for f in flags_str:
                flags |= _JS_REGEX_FLAGS.get(f, 0)
            return re.compile(pattern, flags)
    elif isinstance(obj, dict):
        return {k: _resolve_mongosh_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_mongosh_types(item) for item in obj]
    return obj


def _js_to_json(text):
    """Convert relaxed mongosh object notation to strict JSON.

    Adds double quotes around unquoted identifiers used as object keys
    (e.g. ``{name: "Alice"}`` becomes ``{"name": "Alice"}``).  Also
    converts single-quoted strings to double-quoted strings so that
    expressions like ``{'name': 'Alice'}`` and ``{name: 'Alice'}`` are
    accepted.  JavaScript comments (``//`` and ``/* */``) are stripped.
    Regex literals (``/pattern/flags``) are converted to placeholder
    strings that ``_resolve_mongosh_types`` turns into compiled patterns.
    """
    out = []
    i = 0
    n = len(text)
    # Track last non-whitespace character for regex-vs-comment disambiguation.
    # A '/' in value position (after ':', '[', ',', '(') starts a regex literal;
    # otherwise '//' is a line comment and '/*' is a block comment.
    last_sig = ''

    while i < n:
        ch = text[i]

        # --- slash: comment or regex literal ---
        if ch == '/':
            # regex literal when '/' appears in value position
            if last_sig in (':', '[', ',', '(') and (
                i + 1 >= n or text[i + 1] != '/'
            ):
                # block comment still wins over regex
                if i + 1 < n and text[i + 1] == '*':
                    i += 2
                    while i < n and not (
                        text[i] == '*' and i + 1 < n and text[i + 1] == '/'
                    ):
                        i += 1
                    if i < n:
                        i += 2
                    continue

                # parse /pattern/flags
                i += 1  # skip opening /
                pattern_chars = []
                while i < n and text[i] != '/':
                    if text[i] == '\\' and i + 1 < n:
                        if text[i + 1] == '/':
                            pattern_chars.append('/')
                            i += 2
                        else:
                            pattern_chars.append(text[i])
                            pattern_chars.append(text[i + 1])
                            i += 2
                    else:
                        pattern_chars.append(text[i])
                        i += 1
                if i < n:
                    i += 1  # skip closing /
                flags_chars = []
                while i < n and text[i].isalpha():
                    flags_chars.append(text[i])
                    i += 1
                pattern = ''.join(pattern_chars)
                flags = ''.join(flags_chars)
                placeholder = f'{_MONGOSH_SENTINEL}regex:{flags}:{pattern}'
                out.append(json.dumps(placeholder))
                last_sig = '"'
                continue

            # single-line comment
            if i + 1 < n and text[i + 1] == '/':
                i += 2
                while i < n and text[i] != '\n':
                    i += 1
                continue

            # block comment
            if i + 1 < n and text[i + 1] == '*':
                i += 2
                while i < n and not (
                    text[i] == '*' and i + 1 < n and text[i + 1] == '/'
                ):
                    i += 1
                if i < n:
                    i += 2
                continue

            # bare '/' (e.g. division) — pass through
            out.append(ch)
            last_sig = ch
            i += 1
            continue

        # --- double-quoted string: pass through unchanged ---
        if ch == '"':
            out.append(ch)
            i += 1
            while i < n and text[i] != '"':
                if text[i] == '\\':
                    out.append(text[i])
                    i += 1
                    if i < n:
                        out.append(text[i])
                        i += 1
                else:
                    out.append(text[i])
                    i += 1
            if i < n:
                out.append(text[i])  # closing "
                i += 1
            last_sig = '"'
            continue

        # --- single-quoted string: convert to double-quoted ---
        if ch == "'":
            out.append('"')
            i += 1
            while i < n and text[i] != "'":
                if text[i] == '\\':
                    out.append(text[i])
                    i += 1
                    if i < n:
                        out.append(text[i])
                        i += 1
                else:
                    if text[i] == '"':
                        out.append('\\')
                    out.append(text[i])
                    i += 1
            if i < n:
                out.append('"')  # closing ' → "
                i += 1
            last_sig = '"'
            continue

        # --- unquoted identifier: quote if it is an object key ---
        if ch.isalpha() or ch == '_' or ch == '$':
            start = i
            while i < n and (text[i].isalnum() or text[i] in ('_', '$')):
                i += 1
            ident = text[start:i]

            # peek past whitespace for ':'
            j = i
            while j < n and text[j] in (' ', '\t', '\n', '\r'):
                j += 1

            if j < n and text[j] == ':':
                # object key — wrap in double quotes
                out.append('"')
                out.append(ident)
                out.append('"')
                last_sig = '"'
            else:
                # value position (true, false, null, etc.) — leave as-is
                out.append(ident)
                last_sig = ident[-1] if ident else last_sig
            continue

        # --- whitespace: pass through without updating last_sig ---
        if ch in (' ', '\t', '\n', '\r'):
            out.append(ch)
            i += 1
            continue

        out.append(ch)
        last_sig = ch
        i += 1

    return ''.join(out)


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
    """Parse a single argument: JSON object/array, string, number, or boolean.

    Also handles mongosh JavaScript constructors such as ``new Date("...")``,
    ``ISODate("...")``, ``ObjectId("...")``, and ``new ObjectId("...")``.
    """
    arg_str = arg_str.strip()
    if not arg_str:
        return None

    # Preprocess mongosh extensions (new Date, ObjectId, etc.)
    preprocessed = _preprocess_mongosh_extensions(arg_str)

    # Try JSON first (handles objects, arrays, strings, numbers, booleans, null)
    try:
        return _resolve_mongosh_types(json.loads(preprocessed))
    except json.JSONDecodeError:
        pass

    # Try with single quotes replaced (basic mongosh compatibility)
    if "'" in preprocessed:
        try:
            return _resolve_mongosh_types(json.loads(preprocessed.replace("'", '"')))
        except json.JSONDecodeError:
            pass

    # Try relaxed mongosh syntax (unquoted keys / single-quoted strings)
    try:
        return _resolve_mongosh_types(json.loads(_js_to_json(preprocessed)))
    except (json.JSONDecodeError, ValueError):
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


def _split_statements(text):
    """Split a cell containing multiple mongosh statements.

    Statements are delimited by semicolons or newlines at the top level
    (i.e. outside parentheses, brackets, braces, and strings).  Returns
    a list of non-empty statement strings.
    """
    text = text.strip()
    statements = []
    i = 0
    n = len(text)

    while i < n:
        # Skip whitespace and semicolons between statements
        while i < n and text[i] in " \t\n\r;":
            i += 1
        if i >= n:
            break

        # Consume one statement: scan until all opened parens are closed.
        start = i
        depth = 0
        in_string = False
        string_char = None
        escape = False
        found_paren = False

        while i < n:
            ch = text[i]
            if escape:
                escape = False
                i += 1
                continue
            if ch == "\\":
                escape = True
                i += 1
                continue
            if ch in ('"', "'"):
                if not in_string:
                    in_string = True
                    string_char = ch
                elif ch == string_char:
                    in_string = False
                i += 1
                continue
            if in_string:
                i += 1
                continue
            if ch in ("(", "[", "{"):
                depth += 1
                if ch == "(":
                    found_paren = True
            elif ch in (")", "]", "}"):
                depth -= 1
                if depth == 0 and found_paren and ch == ")":
                    i += 1
                    # Check if a method chain follows (e.g. .count(), .sort())
                    j = i
                    while j < n and text[j] in " \t\n\r":
                        j += 1
                    if j < n and text[j] == ".":
                        # Continue consuming — this is a chained method call
                        i = j
                        continue
                    break
            i += 1

        stmt = text[start:i].strip().rstrip(";").strip()
        if stmt:
            statements.append(stmt)

    return statements


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
    if "." in prefix:
        last_dot = prefix.rindex(".")
        collection = prefix[:last_dot]
        rest = rest[last_dot + 1:]  # "find({...}).sort({...}).limit(5)"
    else:
        # db-level method like db.createCollection("name")
        collection = None
        # rest stays as "createCollection(...)"

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

        # --- Line magic: %mongodb (connect, info, or disconnect) ---
        if cell is None:
            if not line:
                self._show_info()
                return
            if line == "--disconnect":
                self._disconnect()
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

        statements = _split_statements(query)
        if not statements:
            print("Error: No query provided.")
            return

        for stmt in statements:
            try:
                collection_name, chain = _parse_mongosh(stmt)
            except ValueError as e:
                print(f"Parse error: {e}")
                return

            try:
                method_name, args = chain[0]

                # db-level methods (no collection)
                if collection_name is None:
                    self._execute_db(method_name, args)
                    continue

                collection = self._db[collection_name]
                self._execute(collection, collection_name, method_name, args, chain[1:])
            except Exception as e:
                print(f"MongoDB error: {e}")
                return

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

    def _disconnect(self):
        """Close the MongoDB connection."""
        if self._client is None:
            print("Not connected.")
            return
        try:
            self._client.close()
        except Exception:
            pass
        self._client = None
        self._db = None
        self._uri = None
        self._db_name = None
        print("Disconnected.")

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

    def _execute_db(self, method, args):
        """Execute a db-level method (no collection)."""
        if method == "createCollection":
            if not args or not isinstance(args[0], str):
                print("Error: createCollection() requires a collection name string.")
                return
            name = args[0]
            opts = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}
            self._db.create_collection(name, **opts)
            print(f"Created collection: {name}")
        elif method == "dropDatabase":
            name = self._db.name
            self._client.drop_database(self._db)
            print(f"Dropped database: {name}")
        else:
            print(
                f"Unsupported db-level method: {method}\n"
                "Supported: db.createCollection(\"name\"), db.dropDatabase()"
            )

    def _execute(self, collection, col_name, method, args, chain):
        """Execute a MongoDB method with optional cursor chain."""

        # --- Read operations ---
        if method == "find":
            filter_doc = args[0] if len(args) > 0 else {}
            projection = args[1] if len(args) > 1 else None

            # Check if count() is in the chain — convert to countDocuments
            if any(m == "count" for m, _ in chain):
                count = collection.count_documents(filter_doc)
                self.shell.user_ns["_mongodb"] = count
                print(count)
                return

            # Check if explain() is in the chain
            if any(m == "explain" for m, _ in chain):
                explain_chain = [(m, a) for m, a in chain if m != "explain"]
                explain_args = next(
                    (a for m, a in chain if m == "explain"), []
                )
                verbosity = explain_args[0] if explain_args else "queryPlanner"
                cmd = {"find": col_name, "filter": filter_doc}
                if projection:
                    cmd["projection"] = projection
                for m, a in explain_chain:
                    if m == "sort" and a:
                        sort_spec = a[0]
                        if isinstance(sort_spec, dict):
                            cmd["sort"] = sort_spec
                    elif m == "limit" and a:
                        cmd["limit"] = int(a[0])
                    elif m == "skip" and a:
                        cmd["skip"] = int(a[0])
                result = self._db.command("explain", cmd, verbosity=verbosity)
                self.shell.user_ns["_mongodb"] = result
                print(json.dumps(_serialize_doc(result), indent=2, ensure_ascii=False))
                return

            cursor = collection.find(filter_doc, projection)
            cursor = self._apply_cursor_chain(cursor, chain)
            docs = list(cursor)
            self.shell.user_ns["_mongodb"] = docs
            _print_documents(docs)

        elif method == "findOne":
            filter_doc = args[0] if len(args) > 0 else {}
            projection = args[1] if len(args) > 1 else None
            doc = collection.find_one(filter_doc, projection)
            self.shell.user_ns["_mongodb"] = doc
            if doc:
                print(json.dumps(_serialize_doc(doc), indent=2, ensure_ascii=False))
            else:
                print("(no result)")

        elif method == "aggregate":
            pipeline = args[0] if len(args) > 0 else []
            if not isinstance(pipeline, list):
                print("Error: aggregate() requires an array pipeline.")
                return

            # Check if explain() is in the chain
            if any(m == "explain" for m, _ in chain):
                explain_args = next(
                    (a for m, a in chain if m == "explain"), []
                )
                verbosity = explain_args[0] if explain_args else "queryPlanner"
                cmd = {"aggregate": col_name, "pipeline": pipeline, "cursor": {}}
                result = self._db.command("explain", cmd, verbosity=verbosity)
                self.shell.user_ns["_mongodb"] = result
                print(json.dumps(_serialize_doc(result), indent=2, ensure_ascii=False))
                return

            docs = list(collection.aggregate(pipeline))
            self.shell.user_ns["_mongodb"] = docs
            _print_documents(docs)

        elif method == "countDocuments":
            filter_doc = args[0] if len(args) > 0 else {}
            count = collection.count_documents(filter_doc)
            self.shell.user_ns["_mongodb"] = count
            print(count)

        elif method == "estimatedDocumentCount":
            count = collection.estimated_document_count()
            self.shell.user_ns["_mongodb"] = count
            print(count)

        elif method == "count":
            filter_doc = args[0] if len(args) > 0 else {}
            count = collection.count_documents(filter_doc)
            self.shell.user_ns["_mongodb"] = count
            print(count)

        elif method == "distinct":
            if len(args) < 1:
                print("Error: distinct() requires a field name.")
                return
            field = args[0]
            filter_doc = args[1] if len(args) > 1 else {}
            values = collection.distinct(field, filter_doc)
            self.shell.user_ns["_mongodb"] = values
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
            result = collection.delete_many(args[0])
            print(f"Deleted {result.deleted_count} document(s)")

        elif method == "drop":
            collection.drop()
            print(f"Dropped collection: {col_name}")

        # --- Index & schema operations ---
        elif method == "createIndex":
            if len(args) < 1:
                print("Error: createIndex() requires key specification.")
                return
            keys = args[0]
            kwargs = args[1] if len(args) > 1 else {}
            if isinstance(keys, dict):
                keys = list(keys.items())
            if not isinstance(kwargs, dict):
                kwargs = {}
            index_name = collection.create_index(keys, **kwargs)
            print(f"Created index: {index_name}")

        # --- Explain ---
        elif method == "explain":
            print(
                "Error: explain() cannot be called directly.\n"
                "Chain it after a query: db.col.find({}).explain()"
            )

        else:
            print(
                f"Unsupported method: {method}\n"
                "Supported: find, findOne, aggregate, count, countDocuments, distinct,\n"
                "           insertOne, insertMany, updateOne, updateMany,\n"
                "           replaceOne, deleteOne, deleteMany, drop, createIndex"
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
