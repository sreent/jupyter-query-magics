# 🔮 cellspell

A spellbook of Jupyter cell magics for query languages.

Write XPath, Cypher, SPARQL, and MongoDB queries directly in notebook cells — just like `%%sql` for SQL.

## Installation

```bash
pip install cellspell
```

With optional backends:

```bash
pip install cellspell[cypher]    # Neo4j support
pip install cellspell[sparql]    # RDFLib support (local graphs)
pip install cellspell[mongodb]   # PyMongo support
pip install cellspell[all]       # Everything
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

### ✅ `%%xpath` — XPath queries via xmllint

Query XML (and HTML) files using XPath expressions, powered by `xmllint`.

**Prerequisites:** `xmllint` must be installed (`sudo apt-get install libxml2-utils`)

```python
%%writefile books.xml
<?xml version="1.0"?>
<bookstore>
    <book category="fiction">
        <title>The Great Gatsby</title>
        <price>10.99</price>
    </book>
    <book category="tech">
        <title>Python Cookbook</title>
        <price>39.99</price>
    </book>
</bookstore>
```

```python
%xpath_load books.xml
```

```python
%%xpath
//book[@category='tech']/title/text()
```
```
Python Cookbook
```

```python
%%xpath --format
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
| `%xpath_load file.xml` | Set default XML file |
| `%xpath_info` | Show xmllint version and settings |
| `%xpath_validate file.xml` | Check well-formedness |
| `%xpath_validate --dtd s.dtd f.xml` | Validate against DTD |
| `%xpath_validate --xsd s.xsd f.xml` | Validate against XSD |
| `%%xpath [file]` | Run XPath query |
| `%%xpath --format [file]` | Run query, pretty-print XML output |
| `%%xpath --html [file]` | Parse as HTML instead of XML |
| `%%xpath --ns prefix=uri [file]` | Register namespace (repeatable) |

---

### ✅ `%%cypher` — Cypher queries via Neo4j

Run Cypher queries against a Neo4j graph database.

**Prerequisites:** `pip install cellspell[cypher]` and a running Neo4j instance

```python
%cypher_connect bolt://localhost:7687 -u neo4j -p password
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
| `%cypher_connect bolt://host:7687` | Connect (no auth) |
| `%cypher_connect bolt://host:7687 -u user -p pass` | Connect with auth |
| `%cypher_connect bolt://host:7687 -d mydb` | Connect to specific database |
| `%cypher_info` | Show connection info |
| `%%cypher` | Query default connection |
| `%%cypher bolt://host:7687` | Query specific instance inline |
| `%%cypher -d mydb` | Query specific database |

---

### ✅ `%%sparql` — SPARQL queries (local TTL + remote endpoints)

Run SPARQL queries against local RDF files or remote SPARQL endpoints like Wikidata.

**Prerequisites:** `pip install cellspell[sparql]` for local graphs; remote endpoints work with no extra dependencies

#### Local TTL files

```python
%sparql_load scientists.ttl
```

```python
%%sparql
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

#### Remote endpoints (e.g. Wikidata)

```python
%%sparql https://query.wikidata.org/sparql
SELECT ?planet ?planetLabel WHERE {
    ?planet wdt:P31 wd:Q634 .
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}
```

```python
# Set a default endpoint to avoid repeating the URL
%sparql_endpoint https://query.wikidata.org/sparql

%%sparql
SELECT ?country ?countryLabel ?population WHERE {
    ?country wdt:P31 wd:Q6256 ;
             wdt:P1082 ?population .
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}
ORDER BY DESC(?population)
LIMIT 5
```

**All SPARQL commands:**

| Command | Description |
|---------|-------------|
| `%sparql_load file.ttl` | Load TTL/RDF into local graph (additive) |
| `%sparql_load file.rdf --format xml` | Load with explicit format |
| `%sparql_endpoint <url>` | Set default remote endpoint |
| `%sparql_info` | Show loaded graph and endpoint info |
| `%%sparql` | Query local graph (or default endpoint) |
| `%%sparql --local` | Force query against local graph |
| `%%sparql --local file.ttl` | Load file inline and query it |
| `%%sparql <endpoint-url>` | Query remote endpoint inline |

**Supported RDF formats:** `.ttl` (Turtle), `.rdf`/`.xml`/`.owl` (RDF/XML), `.n3`, `.nt` (N-Triples), `.jsonld`, `.trig`, `.nq`

---

### ✅ `%%mongodb` — MongoDB queries via PyMongo

Run MongoDB queries directly in notebook cells.

**Prerequisites:** `pip install cellspell[mongodb]` and a running MongoDB instance

```python
%mongo_connect mongodb://localhost:27017/mydb
```

```python
%%mongodb users
{"age": {"$gt": 25}}
```
```json
{
  "_id": "...",
  "name": "Alice",
  "age": 30,
  "city": "Bangkok"
}

(1 document)
```

```python
%%mongodb users --op aggregate
[
    {"$group": {"_id": "$city", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
]
```

**All MongoDB commands:**

| Command | Description |
|---------|-------------|
| `%mongo_connect mongodb://host:27017/db` | Connect to database |
| `%mongo_connect <uri> -d mydb` | Connect with explicit database |
| `%mongo_info` | Show connection, server, and collections |
| `%%mongodb <collection>` | Find documents (default op) |
| `%%mongodb <col> --op aggregate` | Run aggregation pipeline |
| `%%mongodb <col> --op count` | Count matching documents |
| `%%mongodb <col> --op distinct --field name` | Get distinct values |
| `%%mongodb <col> --op insert` | Insert document(s) |
| `%%mongodb <col> --op delete` | Delete matching documents |
| `%%mongodb <col> --limit 10` | Limit results |
| `%%mongodb <col> --sort {"age":-1}` | Sort results |

---

### 🔜 `%%gql` — ISO GQL queries (planned)

Planned backend: GraphLite

## Google Colab Setup

```python
!apt-get install -y libxml2-utils -qq
!pip install cellspell[all] -q
%load_ext cellspell
```

## Architecture

```
cellspell/
├── __init__.py              # %load_ext cellspell (loads all available)
└── spells/
    ├── xpath.py             # %load_ext cellspell.xpath
    ├── cypher.py            # %load_ext cellspell.cypher
    ├── sparql.py            # %load_ext cellspell.sparql
    ├── mongodb.py           # %load_ext cellspell.mongodb
    └── gql.py               # %load_ext cellspell.gql       (planned)
```

Each spell is self-contained and can be loaded independently. Spells only import
their backend dependencies when loaded, so installing `cellspell` with no extras
only requires IPython.

## Contributing

Adding a new spell:

1. Create `cellspell/spells/yourspell.py`
2. Implement a `@magics_class` with your cell/line magics
3. Implement `load_ipython_extension(ipython)` and `unload_ipython_extension(ipython)`
4. Register it in `cellspell/__init__.py`
5. Add optional dependencies to `pyproject.toml`

## License

MIT
