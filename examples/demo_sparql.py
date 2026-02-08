# %% [markdown]
# # 🔮 cellspell — SPARQL Spell Demo
#
# Run SPARQL queries against RDF files (via rdflib) or SPARQL endpoints (Wikidata, Fuseki, etc.).
#
# ## Prerequisites
#
# - `pip install cellspell[sparql]` (for file-based queries via rdflib)
# - SPARQL endpoints work with no extra dependencies

# %%
# !pip install cellspell[sparql] -q  # Uncomment to install

# %%
%load_ext cellspell.sparql

# %% [markdown]
# ## Part 1: RDF Files (via rdflib)
#
# Load a Turtle file and query it with SPARQL.

# %%
%%writefile scientists.ttl
@prefix ex: <http://example.org/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:einstein a foaf:Person ;
    foaf:name "Albert Einstein" ;
    ex:field "Physics" ;
    ex:birthYear "1879"^^xsd:integer ;
    ex:nationality "German" .

ex:curie a foaf:Person ;
    foaf:name "Marie Curie" ;
    ex:field "Chemistry" ;
    ex:birthYear "1867"^^xsd:integer ;
    ex:nationality "Polish" .

ex:turing a foaf:Person ;
    foaf:name "Alan Turing" ;
    ex:field "Computer Science" ;
    ex:birthYear "1912"^^xsd:integer ;
    ex:nationality "British" .

ex:hopper a foaf:Person ;
    foaf:name "Grace Hopper" ;
    ex:field "Computer Science" ;
    ex:birthYear "1906"^^xsd:integer ;
    ex:nationality "American" .

ex:darwin a foaf:Person ;
    foaf:name "Charles Darwin" ;
    ex:field "Biology" ;
    ex:birthYear "1809"^^xsd:integer ;
    ex:nationality "British" .

# %%
%sparql_load scientists.ttl

# %%
%sparql_info

# %% [markdown]
# ### Query the Loaded Graph

# %%
# List all scientists
%%sparql
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX ex: <http://example.org/>
SELECT ?name ?field WHERE {
    ?person a foaf:Person ;
            foaf:name ?name ;
            ex:field ?field .
}
ORDER BY ?name

# %%
# Computer scientists only
%%sparql
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX ex: <http://example.org/>
SELECT ?name ?year WHERE {
    ?person a foaf:Person ;
            foaf:name ?name ;
            ex:field "Computer Science" ;
            ex:birthYear ?year .
}

# %%
# Born before 1900
%%sparql
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX ex: <http://example.org/>
SELECT ?name ?year WHERE {
    ?person foaf:name ?name ;
            ex:birthYear ?year .
    FILTER(?year < 1900)
}
ORDER BY ?year

# %%
# Count by field
%%sparql
PREFIX ex: <http://example.org/>
SELECT ?field (COUNT(?person) AS ?count) WHERE {
    ?person ex:field ?field .
}
GROUP BY ?field
ORDER BY DESC(?count)

# %%
# ASK query — any American scientists?
%%sparql
PREFIX ex: <http://example.org/>
ASK {
    ?person ex:nationality "American" .
}

# %% [markdown]
# ### One-shot: Load and Query in a Single Cell
#
# Use `--file filename.ttl` to load a file and query it without a separate `%sparql_load` step.

# %%
%%writefile planets.ttl
@prefix ex: <http://example.org/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:earth rdfs:label "Earth" ; ex:radius 6371 .
ex:mars  rdfs:label "Mars"  ; ex:radius 3390 .
ex:jupiter rdfs:label "Jupiter" ; ex:radius 69911 .

# %%
# Load and query in one cell — no %sparql_load needed
%%sparql --file planets.ttl
PREFIX ex: <http://example.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?name ?radius WHERE {
    ?planet rdfs:label ?name ;
            ex:radius ?radius .
}
ORDER BY DESC(?radius)

# %% [markdown]
# ## Part 2: SPARQL Endpoints (Wikidata, Fuseki, etc.)
#
# Query any SPARQL endpoint directly using `--endpoint`.

# %%
# Query Wikidata with --endpoint
%%sparql --endpoint https://query.wikidata.org/sparql
SELECT ?country ?countryLabel ?population WHERE {
    ?country wdt:P31 wd:Q6256 ;
             wdt:P1082 ?population .
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}
ORDER BY DESC(?population)
LIMIT 10

# %%
# Set a default endpoint to avoid repeating the URL
%sparql_endpoint https://query.wikidata.org/sparql

# %%
# Now queries go to the default endpoint
%%sparql
SELECT ?planet ?planetLabel WHERE {
    ?planet wdt:P31 wd:Q634 .
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}

# %%
# Query the file-based graph even with a default endpoint set
%%sparql --file scientists.ttl
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
SELECT ?name WHERE {
    ?person foaf:name ?name .
}
