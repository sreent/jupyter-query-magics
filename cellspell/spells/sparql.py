"""cellspell.spells.sparql — SPARQL cell magic powered by RDFLib and HTTP.

Usage:
    %load_ext cellspell.sparql    # Load only this spell
    %load_ext cellspell           # Or load all spells

Commands:
    %%sparql --file data.ttl                  Query single RDF file (via rdflib)
    %%sparql --files a.ttl,b.ttl              Query multiple RDF files
    %%sparql --endpoint https://host/sparql    Query SPARQL endpoint
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from IPython.core.magic import Magics, cell_magic, magics_class


def _check_rdflib():
    """Check if rdflib is available (needed only for file-based graphs)."""
    try:
        import rdflib  # noqa: F401

        return rdflib
    except ImportError:
        raise RuntimeError(
            "rdflib not found. Install it with:\n"
            "  pip install rdflib\n"
            "  pip install cellspell[sparql]"
        )


def _guess_rdf_format(filename):
    """Guess the RDF serialization format from file extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "ttl": "turtle",
        "turtle": "turtle",
        "n3": "n3",
        "nt": "nt",
        "ntriples": "nt",
        "rdf": "xml",
        "xml": "xml",
        "owl": "xml",
        "jsonld": "json-ld",
        "json": "json-ld",
        "trig": "trig",
        "nq": "nquads",
    }.get(ext, "turtle")


def _format_sparql_results(results):
    """Format rdflib SPARQL SELECT results as a text table."""
    rows = list(results)
    if not rows:
        return "(no results)"

    keys = [str(v) for v in results.vars]
    str_rows = []
    for row in rows:
        str_rows.append([str(val) if val is not None else "" for val in row])

    col_widths = [len(k) for k in keys]
    for row in str_rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(val))

    header = " | ".join(k.ljust(col_widths[i]) for i, k in enumerate(keys))
    separator = "-+-".join("-" * w for w in col_widths)

    lines = [header, separator]
    for row in str_rows:
        lines.append(" | ".join(val.ljust(col_widths[i]) for i, val in enumerate(row)))

    lines.append(f"\n({len(str_rows)} row{'s' if len(str_rows) != 1 else ''})")
    return "\n".join(lines)


def _query_remote_endpoint(endpoint, query):
    """Send a SPARQL query to an HTTP endpoint and return formatted results."""
    data = urllib.parse.urlencode({"query": query}).encode("utf-8")
    headers = {
        "Accept": "application/sparql-results+json, application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "cellspell/0.1 (Jupyter SPARQL magic)",
    }

    req = urllib.request.Request(endpoint, data=data, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {e.code} from endpoint:\n{error_body}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Cannot reach endpoint: {e.reason}")

    result = json.loads(body)

    if "results" in result and "bindings" in result["results"]:
        return _format_json_sparql_results(result)
    elif "boolean" in result:
        return f"Result: {result['boolean']}"
    else:
        return body


def _format_json_sparql_results(result):
    """Format JSON SPARQL results (application/sparql-results+json) as a text table."""
    keys = result["head"]["vars"]
    bindings = result["results"]["bindings"]

    if not bindings:
        return "(no results)"

    str_rows = []
    for binding in bindings:
        row = []
        for k in keys:
            if k in binding:
                row.append(binding[k].get("value", ""))
            else:
                row.append("")
        str_rows.append(row)

    col_widths = [len(k) for k in keys]
    for row in str_rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(val))

    header = " | ".join(k.ljust(col_widths[i]) for i, k in enumerate(keys))
    separator = "-+-".join("-" * w for w in col_widths)

    lines = [header, separator]
    for row in str_rows:
        lines.append(" | ".join(val.ljust(col_widths[i]) for i, val in enumerate(row)))

    lines.append(f"\n({len(str_rows)} row{'s' if len(str_rows) != 1 else ''})")
    return "\n".join(lines)


@magics_class
class SPARQLMagics(Magics):
    """Jupyter magics for running SPARQL queries."""

    _graph = None
    _loaded_files = []

    @cell_magic
    def sparql(self, line, cell):
        """Run a SPARQL query.

        Usage:
            %%sparql --file data.ttl                   Query single RDF file (rdflib)
            %%sparql --files a.ttl,b.ttl               Query multiple RDF files
            %%sparql --endpoint https://host/sparql     Query SPARQL endpoint
        """
        parts = line.strip().split()
        endpoint = None
        rdf_file = None
        rdf_files = None
        rdf_format = None

        i = 0
        while i < len(parts):
            if parts[i] in ("--endpoint", "-e") and i + 1 < len(parts):
                endpoint = parts[i + 1]
                i += 2
            elif parts[i] in ("--file", "-f") and i + 1 < len(parts):
                rdf_file = parts[i + 1]
                i += 2
            elif parts[i] == "--files" and i + 1 < len(parts):
                rdf_files = [f.strip() for f in parts[i + 1].split(",") if f.strip()]
                i += 2
            elif parts[i] == "--format" and i + 1 < len(parts):
                rdf_format = parts[i + 1]
                i += 2
            else:
                print(f"Unknown option: {parts[i]}")
                return

        query = cell.strip()
        if not query:
            print("Error: No SPARQL query provided.")
            return

        # Check for conflicting options
        file_opts = sum(1 for x in [rdf_file, rdf_files] if x)
        if file_opts > 1:
            print("Error: Cannot use --file and --files together. Use --files for multiple files.")
            return
        if (rdf_file or rdf_files) and endpoint:
            print("Error: Cannot use --file/--files and --endpoint together.")
            return

        if rdf_files:
            for f in rdf_files:
                self._load_file(f, rdf_format)
            self._query_graph(query)
        elif rdf_file:
            self._load_file(rdf_file, rdf_format)
            self._query_graph(query)
        elif endpoint:
            self._query_endpoint(endpoint, query)
        else:
            print(
                "Error: Specify --file, --files, or --endpoint.\n"
                "Use: %%sparql --file data.ttl            (query single RDF file)\n"
                "     %%sparql --files a.ttl,b.ttl        (query multiple RDF files)\n"
                "  or: %%sparql --endpoint <url>           (query SPARQL endpoint)"
            )

    def _load_file(self, filepath, rdf_format=None):
        """Load an RDF file into the in-memory graph."""
        rdflib = _check_rdflib()
        from pathlib import Path

        if not Path(filepath).exists():
            print(f"Error: File not found: {filepath}")
            return

        if rdf_format is None:
            rdf_format = _guess_rdf_format(filepath)

        if self._graph is None:
            self._graph = rdflib.Graph()

        # Skip if already loaded
        if filepath in self._loaded_files:
            return

        try:
            before = len(self._graph)
            self._graph.parse(filepath, format=rdf_format)
            added = len(self._graph) - before
            self._loaded_files.append(filepath)
            print(f"✓ Loaded: {filepath} (+{added} triples, {len(self._graph)} total)")
        except Exception as e:
            print(f"Error loading {filepath}: {e}")

    def _query_graph(self, query):
        """Execute SPARQL against the in-memory rdflib graph."""
        _check_rdflib()

        if self._graph is None or len(self._graph) == 0:
            print("Error: No graph loaded.")
            return

        try:
            results = self._graph.query(query)
        except Exception as e:
            print(f"SPARQL error: {e}")
            return

        if hasattr(results, "vars") and results.vars:
            print(_format_sparql_results(results))
        elif hasattr(results, "graph"):
            output = results.graph.serialize(format="turtle")
            if not output.strip():
                print("(no results)")
            else:
                print(output)
        elif hasattr(results, "askAnswer"):
            print(f"Result: {results.askAnswer}")
        else:
            for row in results:
                print(row)

    def _query_endpoint(self, endpoint, query):
        """Execute SPARQL against an HTTP SPARQL endpoint."""
        try:
            output = _query_remote_endpoint(endpoint, query)
            print(output)
        except RuntimeError as e:
            print(f"SPARQL error: {e}")
        except Exception as e:
            print(f"SPARQL error: {e}")


def load_ipython_extension(ipython):
    """Load the SPARQL spell.

    Usage: %load_ext cellspell.sparql
    """
    ipython.register_magics(SPARQLMagics)
    print("✓ sparql spell loaded — %%sparql")


def unload_ipython_extension(ipython):
    """Unload the SPARQL spell."""
    pass
