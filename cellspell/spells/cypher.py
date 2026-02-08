"""cellspell.spells.cypher — Cypher cell magic powered by Neo4j.

Usage:
    %load_ext cellspell.cypher    # Load only this spell
    %load_ext cellspell           # Or load all spells

Commands:
    %cypher bolt://host:7687 -u neo4j -p pass   Connect with auth
    %cypher                                      Show connection info
    %%cypher                                     Query using stored connection
"""

from IPython.core.magic import Magics, line_cell_magic, magics_class


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

    def _connect(self, uri, user=None, password=None, database=None):
        """Connect to a Neo4j instance."""
        neo4j = _check_neo4j()

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

            self._driver.verify_connectivity()
            print(f"✓ Connected to {uri}")
            if database:
                print(f"  Database: {database}")
        except Exception as e:
            self._driver = None
            self._uri = None
            self._database = None
            print(f"Connection failed: {e}")

    def _show_info(self):
        """Show current Neo4j connection info."""
        if self._driver is None:
            print("Not connected. Use %cypher bolt://host:7687")
            return

        print(f"URI:      {self._uri}")
        print(f"Database: {self._database or '(default)'}")
        try:
            info = self._driver.get_server_info()
            print(f"Server:   {info.agent}")
        except Exception as e:
            print(f"Server:   (unable to retrieve — {e})")

    def _disconnect(self):
        """Close the Neo4j connection."""
        if self._driver is None:
            print("Not connected.")
            return
        try:
            self._driver.close()
        except Exception:
            pass
        self._driver = None
        self._uri = None
        self._database = None
        print("Disconnected.")

    def _parse_and_connect(self, line):
        """Parse connection string with optional flags and connect."""
        parts = line.strip().split()
        if not parts:
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

        self._connect(uri, user, password, database)

    @line_cell_magic
    def cypher(self, line, cell=None):
        """Connect to Neo4j or run a Cypher query.

        Line magic — connect or show info:
            %cypher bolt://localhost:7687 -u neo4j -p pass   Connect
            %cypher bolt://host:7687 -d mydb                 Connect with database
            %cypher                                          Show connection info

        Cell magic — run Cypher query:
            %%cypher
            MATCH (n) RETURN n LIMIT 10

            %%cypher -d mydb
            MATCH (n) RETURN n LIMIT 10
        """
        line = line.strip()

        # --- Line magic: %cypher (connect, info, or disconnect) ---
        if cell is None:
            if not line:
                self._show_info()
                return
            if line == "--disconnect":
                self._disconnect()
                return
            self._parse_and_connect(line)
            return

        # --- Cell magic: %%cypher (run query) ---
        database = self._database

        # Parse optional flags on the %%cypher line
        if line:
            parts = line.split()
            i = 0
            while i < len(parts):
                if parts[i] in ("-d", "--database") and i + 1 < len(parts):
                    database = parts[i + 1]
                    i += 2
                else:
                    print(f"Unknown option: {parts[i]}")
                    return

        if self._driver is None:
            print(
                "Error: No connection.\n"
                "Use: %cypher bolt://host:7687"
            )
            return

        query = cell.strip()
        if not query:
            print("Error: No Cypher query provided.")
            return

        try:
            with self._driver.session(database=database) as session:
                result = session.run(query)
                keys = list(result.keys())
                records = [dict(record) for record in result]
                summary = result.consume()

            if records:
                self.shell.user_ns["_cypher"] = records
                print(_format_table(records, keys))
                print(f"\n({len(records)} row{'s' if len(records) != 1 else ''})")
            else:
                counters = summary.counters
                counter_lines = []
                if counters.nodes_created:
                    counter_lines.append(f"Nodes created: {counters.nodes_created}")
                if counters.nodes_deleted:
                    counter_lines.append(f"Nodes deleted: {counters.nodes_deleted}")
                if counters.relationships_created:
                    counter_lines.append(
                        f"Relationships created: {counters.relationships_created}"
                    )
                if counters.relationships_deleted:
                    counter_lines.append(
                        f"Relationships deleted: {counters.relationships_deleted}"
                    )
                if counters.properties_set:
                    counter_lines.append(f"Properties set: {counters.properties_set}")
                if counters.labels_added:
                    counter_lines.append(f"Labels added: {counters.labels_added}")
                if counters.labels_removed:
                    counter_lines.append(f"Labels removed: {counters.labels_removed}")
                if counter_lines:
                    print("\n".join(counter_lines))
                else:
                    print("(no results)")
        except Exception as e:
            print(f"Cypher error: {e}")


def load_ipython_extension(ipython):
    """Load the Cypher spell.

    Usage: %load_ext cellspell.cypher
    """
    ipython.register_magics(CypherMagics)
    print("✓ cypher spell loaded — %cypher, %%cypher")


def unload_ipython_extension(ipython):
    """Unload the Cypher spell."""
    pass
