# 🔮 cellspell

A spellbook of Jupyter cell magics for query languages.

Write XPath, Cypher, SPARQL, and MongoDB queries directly in notebook cells — just like `%%sql` for SQL.

## Installation

```bash
pip install git+https://github.com/sreent/jupyter-query-magics.git
```

With optional backends:

```bash
pip install "git+https://github.com/sreent/jupyter-query-magics.git#egg=cellspell[cypher]"    # Neo4j support
pip install "git+https://github.com/sreent/jupyter-query-magics.git#egg=cellspell[sparql]"    # RDFLib support (local graphs)
pip install "git+https://github.com/sreent/jupyter-query-magics.git#egg=cellspell[mongodb]"   # PyMongo support
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
| `%%xpath --format file.xml` | Run query, pretty-print XML output |
| `%%xpath --html file.html` | Parse as HTML instead of XML |
| `%%xpath --ns prefix=uri file.xml` | Register namespace (repeatable) |

---

### ✅ `%%cypher` — Cypher queries via Neo4j

Run Cypher queries against a Neo4j graph database.

**Prerequisites:** `pip install cellspell[cypher]` and a running Neo4j instance

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

---

### ✅ `%%sparql` — SPARQL queries (files + endpoints)

Run SPARQL queries against RDF files (via rdflib) or SPARQL endpoints (Wikidata, Fuseki, etc.).

**Prerequisites:** `pip install cellspell[sparql]` for file-based queries; endpoints work with no extra dependencies

#### RDF files (via rdflib)

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

#### SPARQL endpoints (Wikidata, Fuseki, etc.)

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

---

### ✅ `%%mongodb` — MongoDB queries via PyMongo

Run MongoDB queries directly in notebook cells using mongosh syntax.

**Prerequisites:** `pip install cellspell[mongodb]` and a running MongoDB instance

```python
%mongodb mongodb://admin:secret@localhost:27017/mydb
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

```python
%%mongodb
db.users.countDocuments({"active": true})
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

---

### 🔜 `%%gql` — ISO GQL queries (planned)

Planned backend: GraphLite

## Google Colab Setup

```python
!apt-get install -y libxml2-utils -qq
!pip install cellspell[all] -q
%load_ext cellspell
```

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

# Then in the next cell:
_cypher  # [{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}]
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
