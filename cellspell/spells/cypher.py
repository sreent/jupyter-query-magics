"""cellspell.spells.cypher — Cypher cell magic powered by Neo4j.

Usage:
    %load_ext cellspell.cypher    # Load only this spell
    %load_ext cellspell           # Or load all spells

Commands:
    %cypher_connect bolt://host:7687             Connect with no auth
    %cypher_connect bolt://host:7687 -u neo4j -p pass  Connect with auth
    %cypher_info                                 Show connection info

    %%cypher                      Query default connection
    %%cypher bolt://host:7687     Query specific instance
"""

from IPython.core.magic import Magics, cell_magic, line_magic, magics_class


def _check_neo4j():
    """Check if the neo4j driver is available."""
    try:
        import neo4j  # noqa: F401

        return neo4j
    except ImportError:
        raise RuntimeError(
            "neo4j driver not found. Install it with:\n"
            "  pip install neo4j\n"
            "  pip install cellspell[cypher]"
        )


def _format_table(records, keys):
    """Format query results as an aligned text table."""
    if not records:
        return "(no results)"

    str_rows = []
    for rec in records:
        str_rows.append([str(rec.get(k, "")) for k in keys])

    col_widths = [len(k) for k in keys]
    for row in str_rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(val))

    header = " | ".join(k.ljust(col_widths[i]) for i, k in enumerate(keys))
    separator = "-+-".join("-" * w for w in col_widths)

    lines = [header, separator]
    for row in str_rows:
        lines.append(" | ".join(val.ljust(col_widths[i]) for i, val in enumerate(row)))

    return "\n".join(lines)


@magics_class
class CypherMagics(Magics):
    """Jupyter magics for running Cypher queries via Neo4j."""

    _driver = None
    _uri = None
    _database = None

    @line_magic
    def cypher_connect(self, line):
        """Connect to a Neo4j instance.

        Usage:
            %cypher_connect bolt://localhost:7687
            %cypher_connect bolt://localhost:7687 -u neo4j -p password
            %cypher_connect bolt://localhost:7687 -d mydb
        """
        neo4j = _check_neo4j()

        parts = line.strip().split()
        if not parts:
            if self._uri:
                print(f"Current connection: {self._uri}")
            else:
                print("No connection. Usage: %cypher_connect bolt://host:7687")
            return

        uri = parts[0]
        user = None
        password = None
        database = None

        i = 1
        while i < len(parts):
            if parts[i] in ("-u", "--user") and i + 1 < len(parts):
                user = parts[i + 1]
                i += 2
            elif parts[i] in ("-p", "--password") and i + 1 < len(parts):
                password = parts[i + 1]
                i += 2
            elif parts[i] in ("-d", "--database") and i + 1 < len(parts):
                database = parts[i + 1]
                i += 2
            else:
                print(f"Unknown option: {parts[i]}")
                return

        # Close existing connection
        if self._driver is not None:
            try:
                self._driver.close()
            except Exception:
                pass

        try:
            if user and password:
                auth = neo4j.auth.basic_auth(user, password)
                self._driver = neo4j.GraphDatabase.driver(uri, auth=auth)
            else:
                self._driver = neo4j.GraphDatabase.driver(uri)

            self._uri = uri
            self._database = database

            # Verify connectivity
            self._driver.verify_connectivity()
            print(f"✓ Connected to {uri}")
            if database:
                print(f"  Database: {database}")
        except Exception as e:
            self._driver = None
            self._uri = None
            self._database = None
            print(f"Connection failed: {e}")

    @line_magic
    def cypher_info(self, line):
        """Show current Cypher connection info."""
        _check_neo4j()
        if self._driver is None:
            print("Not connected. Use %cypher_connect bolt://host:7687")
            return

        print(f"URI:      {self._uri}")
        print(f"Database: {self._database or '(default)'}")
        try:
            info = self._driver.get_server_info()
            print(f"Server:   {info.agent}")
        except Exception as e:
            print(f"Server:   (unable to retrieve — {e})")

    @cell_magic
    def cypher(self, line, cell):
        """Run a Cypher query against a Neo4j instance.

        Usage:
            %%cypher
            MATCH (n) RETURN n LIMIT 10

            %%cypher bolt://host:7687
            MATCH (n) RETURN n LIMIT 10
        """
        neo4j = _check_neo4j()

        parts = line.strip().split()
        driver = self._driver
        database = self._database
        temp_driver = None

        i = 0
        while i < len(parts):
            if parts[i] in ("-d", "--database") and i + 1 < len(parts):
                database = parts[i + 1]
                i += 2
            elif not parts[i].startswith("-"):
                # Inline URI — create a temporary driver
                try:
                    temp_driver = neo4j.GraphDatabase.driver(parts[i])
                    driver = temp_driver
                except Exception as e:
                    print(f"Connection failed: {e}")
                    return
                i += 1
            else:
                print(f"Unknown option: {parts[i]}")
                return

        if driver is None:
            print(
                "Error: No connection.\n"
                "Use: %cypher_connect bolt://host:7687\n"
                "  or: %%cypher bolt://host:7687"
            )
            return

        query = cell.strip()
        if not query:
            print("Error: No Cypher query provided.")
            return

        try:
            with driver.session(database=database) as session:
                result = session.run(query)
                records = [dict(record) for record in result]
                keys = list(result.keys()) if hasattr(result, "keys") else []

                if not keys and records:
                    keys = list(records[0].keys())

                summary = result.consume()

            if records:
                print(_format_table(records, keys))
                print(f"\n({len(records)} row{'s' if len(records) != 1 else ''})")
            else:
                counters = summary.counters
                parts = []
                if counters.nodes_created:
                    parts.append(f"Nodes created: {counters.nodes_created}")
                if counters.nodes_deleted:
                    parts.append(f"Nodes deleted: {counters.nodes_deleted}")
                if counters.relationships_created:
                    parts.append(f"Relationships created: {counters.relationships_created}")
                if counters.relationships_deleted:
                    parts.append(f"Relationships deleted: {counters.relationships_deleted}")
                if counters.properties_set:
                    parts.append(f"Properties set: {counters.properties_set}")
                if counters.labels_added:
                    parts.append(f"Labels added: {counters.labels_added}")
                if counters.labels_removed:
                    parts.append(f"Labels removed: {counters.labels_removed}")
                if parts:
                    print("\n".join(parts))
                else:
                    print("(no results)")
        except Exception as e:
            print(f"Cypher error: {e}")
        finally:
            if temp_driver is not None:
                try:
                    temp_driver.close()
                except Exception:
                    pass


def load_ipython_extension(ipython):
    """Load the Cypher spell.

    Usage: %load_ext cellspell.cypher
    """
    _check_neo4j()
    ipython.register_magics(CypherMagics)
    print("✓ cypher spell loaded — %cypher_connect, %cypher_info, %%cypher")


def unload_ipython_extension(ipython):
    """Unload the Cypher spell."""
    pass
