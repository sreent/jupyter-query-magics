# 🔮 cellspell

A spellbook of Jupyter cell magics for query languages.

Write XPath, Cypher, SPARQL, and MongoDB queries directly in notebook cells — just like `%%sql` for SQL.

## Installation

```bash
pip install cellspell
```

With optional backends:

```bash
pip install cellspell[cypher]    # Neo4j + KùzuDB support
pip install cellspell[sparql]    # RDFLib support
pip install cellspell[mongodb]   # PyMongo support
pip install cellspell[all]       # Everything
```

## Quick Start

```python
# Load all available spells
%load_ext cellspell

# Or load individual spells
%load_ext cellspell.xpath
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

### 🔜 `%%cypher` — Cypher queries (planned)

```python
%cypher_connect bolt://localhost:7687
```

```python
%%cypher
MATCH (p:Person)-[:KNOWS]->(q:Person)
RETURN p.name, q.name
```

Planned backends: Neo4j, KùzuDB

### 🔜 `%%sparql` — SPARQL queries (planned)

```python
%%sparql https://dbpedia.org/sparql
SELECT ?name WHERE {
    ?person a dbo:Scientist ;
            rdfs:label ?name .
    FILTER(LANG(?name) = "en")
} LIMIT 10
```

Planned backends: RDFLib, Oxigraph, remote endpoints

### 🔜 `%%mongodb` — MongoDB queries (planned)

```python
%mongo_connect mongodb://localhost:27017/mydb
```

```python
%%mongodb
db.users.find({ "age": { "$gt": 25 } })
```

Planned backend: PyMongo

### 🔜 `%%gql` — ISO GQL queries (planned)

```python
%%gql
MATCH (p:Person)-[:KNOWS]->(q:Person)
RETURN p.name, q.name
```

Planned backend: GraphLite

## Google Colab Setup

```python
!apt-get install -y libxml2-utils -qq
!pip install cellspell -q
%load_ext cellspell
```

## Architecture

```
cellspell/
├── __init__.py              # %load_ext cellspell (loads all)
└── spells/
    ├── xpath.py             # %load_ext cellspell.xpath
    ├── cypher.py            # %load_ext cellspell.cypher    (planned)
    ├── sparql.py            # %load_ext cellspell.sparql    (planned)
    ├── mongodb.py           # %load_ext cellspell.mongodb   (planned)
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
