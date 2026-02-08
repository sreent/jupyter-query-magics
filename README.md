# 🔮 cellspell

A spellbook of Jupyter cell magics for query languages.

Write XPath, Cypher, SPARQL, and MongoDB queries directly in notebook cells — just like `%%sql` for SQL.

## Installation

```bash
pip install git+https://github.com/sreent/jupyter-query-magics.git
```

With optional backends:

```bash
pip install "git+https://github.com/sreent/jupyter-query-magics.git#egg=cellspell[cypher]"    # Neo4j
pip install "git+https://github.com/sreent/jupyter-query-magics.git#egg=cellspell[sparql]"    # RDFLib
pip install "git+https://github.com/sreent/jupyter-query-magics.git#egg=cellspell[mongodb]"   # PyMongo
pip install "git+https://github.com/sreent/jupyter-query-magics.git#egg=cellspell[all]"       # Everything
```

## Quick Start

```python
# Load all available spells (skips those without backends installed)
%load_ext cellspell

# Or load individual spells
%load_ext cellspell.xpath
%load_ext cellspell.cypher
%load_ext cellspell.sparql
%load_ext cellspell.mongodb
```

## Spells

### `%xpath` / `%%xpath` — XPath queries via xmllint

Query XML (and HTML) files using XPath expressions, powered by `xmllint`.

**Prerequisites:** `xmllint` must be installed:

```bash
# Ubuntu/Debian
sudo apt-get install libxml2-utils

# macOS
brew install libxml2
```

**Example:**

```python
%%xpath books.xml
//book[@category='tech']/title/text()
```
```
Python Cookbook
```

```python
%%xpath --format books.xml
//book[@category='tech']
```
```xml
<book category="tech">
  <title>Python Cookbook</title>
  <price>39.99</price>
</book>
```

**All XPath commands:**

| Command | Description |
|---------|-------------|
| `%xpath` | Show xmllint version |
| `%xpath file.xml` | Check well-formedness |
| `%xpath --dtd s.dtd f.xml` | Validate against DTD |
| `%xpath --xsd s.xsd f.xml` | Validate against XSD |
| `%xpath --rng s.rng f.xml` | Validate against RelaxNG |
| `%%xpath file.xml` | Run XPath query |
| `%%xpath --format file.xml` | Pretty-print XML output |
| `%%xpath --html file.html` | Parse as HTML instead of XML |
| `%%xpath --ns prefix=uri file.xml` | Register namespace (repeatable) |

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sreent/jupyter-query-magics/blob/main/examples/colab_xpath.ipynb)

---

### `%cypher` / `%%cypher` — Cypher queries via Neo4j

Run Cypher queries against a Neo4j graph database.

**Prerequisites:** A running Neo4j instance and:

```bash
pip install "git+https://github.com/sreent/jupyter-query-magics.git#egg=cellspell[cypher]"
```

**Example:**

```python
%cypher bolt://localhost:7687 -u neo4j -p password
```

```python
%%cypher
CREATE (a:Person {name: 'Alice', age: 30}),
       (b:Person {name: 'Bob', age: 25}),
       (a)-[:KNOWS]->(b)
```
```
Nodes created: 2
Relationships created: 1
Properties set: 4
```

```python
%%cypher
MATCH (p:Person)-[:KNOWS]->(q:Person)
RETURN p.name AS person, q.name AS knows
```
```
person | knows
-------+------
Alice  | Bob

(1 row)
```

**All Cypher commands:**

| Command | Description |
|---------|-------------|
| `%cypher bolt://host:7687` | Connect (no auth) |
| `%cypher bolt://host:7687 -u user -p pass` | Connect with auth |
| `%cypher bolt://host:7687 -d mydb` | Connect to specific database |
| `%cypher` | Show connection info |
| `%cypher --disconnect` | Close connection |
| `%%cypher` | Query using stored connection |
| `%%cypher -d mydb` | Query specific database |

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sreent/jupyter-query-magics/blob/main/examples/colab_cypher.ipynb)

---

### `%sparql` / `%%sparql` — SPARQL queries (files + endpoints)

Run SPARQL queries against RDF files (via rdflib) or SPARQL endpoints (Wikidata, Fuseki, etc.).

**Prerequisites:** For file-based queries:

```bash
pip install "git+https://github.com/sreent/jupyter-query-magics.git#egg=cellspell[sparql]"
```

Endpoint queries work with no extra dependencies.

**RDF files (via rdflib):**

```python
%%sparql --file scientists.ttl
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
SELECT ?name WHERE {
    ?person foaf:name ?name .
}
```
```
name
-----------------
Albert Einstein
Marie Curie
Alan Turing

(3 rows)
```

**SPARQL endpoints (Wikidata, Fuseki, etc.):**

```python
%%sparql --endpoint https://query.wikidata.org/sparql
SELECT ?planet ?planetLabel WHERE {
    ?planet wdt:P31 wd:Q634 .
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}
```

**All SPARQL commands:**

| Command | Description |
|---------|-------------|
| `%sparql` | Show loaded graph info |
| `%sparql --reset` | Clear loaded graph |
| `%%sparql --file data.ttl` | Query single RDF file (via rdflib) |
| `%%sparql --files a.ttl,b.ttl` | Query multiple RDF files (merged graph) |
| `%%sparql --file data.rdf --format xml` | Query with explicit RDF format |
| `%%sparql --endpoint <url>` | Query SPARQL endpoint |

**Supported RDF formats:** `.ttl` (Turtle), `.rdf`/`.xml`/`.owl` (RDF/XML), `.n3`, `.nt` (N-Triples), `.jsonld`, `.trig`, `.nq`

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sreent/jupyter-query-magics/blob/main/examples/colab_sparql.ipynb)

---

### `%mongodb` / `%%mongodb` — MongoDB queries via PyMongo

Run MongoDB queries directly in notebook cells using mongosh syntax.

**Prerequisites:** A running MongoDB instance and:

```bash
pip install "git+https://github.com/sreent/jupyter-query-magics.git#egg=cellspell[mongodb]"
```

**Example:**

```python
# Local server
%mongodb mongodb://localhost:27017/mydb

# MongoDB Atlas (cloud)
%mongodb mongodb+srv://user:pass@cluster0.abc123.mongodb.net/mydb
```

```python
%%mongodb
db.users.find({"age": {"$gt": 25}}).sort({"age": -1}).limit(5)
```
```json
{
  "name": "Alice",
  "age": 30,
  "city": "Bangkok"
}

(1 document)
```

```python
%%mongodb
db.users.aggregate([
    {"$group": {"_id": "$city", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
])
```

**All MongoDB commands:**

| Command | Description |
|---------|-------------|
| `%mongodb mongodb://user:pass@host:27017/mydb` | Connect to database |
| `%mongodb mongodb+srv://user:pass@cluster.mongodb.net/mydb` | Connect to MongoDB Atlas |
| `%mongodb mongodb://host:27017 -d mydb` | Connect with explicit database |
| `%mongodb` | Show connection info |
| `%mongodb --disconnect` | Close connection |
| `%%mongodb` | Query using stored connection |
| `%%mongodb mongodb://user:pass@host:27017/mydb` | Connect and query in one cell |

**Supported methods:**

| Method | Description |
|--------|-------------|
| `db.col.find(filter, projection)` | Query documents (chain `.sort()`, `.limit()`, `.skip()`) |
| `db.col.findOne(filter, projection)` | Return single document |
| `db.col.aggregate(pipeline)` | Run aggregation pipeline |
| `db.col.countDocuments(filter)` | Count matching documents |
| `db.col.estimatedDocumentCount()` | Fast estimated count |
| `db.col.distinct(field, filter)` | Get distinct values |
| `db.col.insertOne(doc)` | Insert one document |
| `db.col.insertMany([docs])` | Insert multiple documents |
| `db.col.updateOne(filter, update)` | Update first match |
| `db.col.updateMany(filter, update)` | Update all matches |
| `db.col.replaceOne(filter, doc)` | Replace first match |
| `db.col.deleteOne(filter)` | Delete first match |
| `db.col.deleteMany(filter)` | Delete all matches |
| `db.col.drop()` | Drop collection |

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sreent/jupyter-query-magics/blob/main/examples/colab_mongodb.ipynb)

---

### 🔜 `%%gql` — ISO GQL queries (planned)

Support for the ISO GQL (Graph Query Language) standard is planned.

## Output Variables

Each spell stores the last query result in a Python variable for further processing:

| Spell | Variable | Type |
|-------|----------|------|
| XPath | `_xpath` | `str` (raw output text) |
| Cypher | `_cypher` | `list[dict]` (rows as dicts) |
| SPARQL | `_sparql` | `list[dict]` (rows as dicts) |
| MongoDB | `_mongodb` | `list[dict]`, `dict`, `int`, or `list` (depends on method) |

```python
%%cypher
MATCH (p:Person) RETURN p.name AS name, p.age AS age
```

Then in the next cell:

```python
_cypher  # [{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}]
```

## Google Colab

Each spell has a ready-to-run Colab notebook with full setup (server install, sample data, queries):

| Spell | Colab Notebook |
|-------|----------------|
| XPath | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sreent/jupyter-query-magics/blob/main/examples/colab_xpath.ipynb) |
| Cypher | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sreent/jupyter-query-magics/blob/main/examples/colab_cypher.ipynb) |
| SPARQL | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sreent/jupyter-query-magics/blob/main/examples/colab_sparql.ipynb) |
| MongoDB | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sreent/jupyter-query-magics/blob/main/examples/colab_mongodb.ipynb) |

## Architecture

```
cellspell/
├── __init__.py              # %load_ext cellspell (loads all available)
├── xpath.py                 # Convenience re-export for %load_ext cellspell.xpath
├── cypher.py                # Convenience re-export for %load_ext cellspell.cypher
├── sparql.py                # Convenience re-export for %load_ext cellspell.sparql
├── mongodb.py               # Convenience re-export for %load_ext cellspell.mongodb
└── spells/
    ├── xpath.py             # XPath magic (xmllint)
    ├── cypher.py            # Cypher magic (neo4j driver)
    ├── sparql.py            # SPARQL magic (rdflib + HTTP)
    ├── mongodb.py           # MongoDB magic (pymongo)
    └── gql.py               # GQL magic (planned)

tests/
├── test_mongodb_parser.py   # Mongosh syntax parser tests
├── test_sparql_parser.py    # SPARQL formatting & helper tests
└── test_xpath_helpers.py    # XPath formatting tests

examples/
├── colab_xpath.ipynb        # Colab notebook — XPath
├── colab_cypher.ipynb       # Colab notebook — Cypher
├── colab_sparql.ipynb       # Colab notebook — SPARQL
├── colab_mongodb.ipynb      # Colab notebook — MongoDB
├── demo_xpath.py            # Percent-script demo — XPath
├── demo_cypher.py           # Percent-script demo — Cypher
├── demo_sparql.py           # Percent-script demo — SPARQL
└── demo_mongodb.py          # Percent-script demo — MongoDB
```

Each spell is self-contained and can be loaded independently. Spells only import
their backend dependencies when used, so installing `cellspell` with no extras
only requires IPython.

## Contributing

Adding a new spell:

1. Create `cellspell/spells/yourspell.py`
2. Implement a `@magics_class` with `@line_cell_magic` (for `%spell` / `%%spell`)
3. Implement `load_ipython_extension(ipython)` and `unload_ipython_extension(ipython)`
4. Create `cellspell/yourspell.py` wrapper for `%load_ext cellspell.yourspell`
5. Register it in `cellspell/__init__.py`
6. Add optional dependencies to `pyproject.toml`
7. Add tests in `tests/`
8. Run tests: `python -m pytest tests/ -v`

## License

MIT
