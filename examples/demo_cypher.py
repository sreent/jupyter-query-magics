# %% [markdown]
# # 🔮 cellspell — Cypher Spell Demo
#
# Run Cypher queries against Neo4j directly in Jupyter cells.
#
# ## Prerequisites
#
# - A running Neo4j instance (local or remote)
# - `pip install cellspell[cypher]`

# %%
# !pip install cellspell[cypher] -q  # Uncomment to install

# %%
%load_ext cellspell.cypher

# %% [markdown]
# ## Connect to Neo4j

# %%
# Connect with authentication
%cypher_connect bolt://localhost:7687 -u neo4j -p password

# %%
%cypher_info

# %% [markdown]
# ## Create Sample Data

# %%
%%cypher
CREATE (a:Person {name: 'Alice', age: 30}),
       (b:Person {name: 'Bob', age: 25}),
       (c:Person {name: 'Charlie', age: 35}),
       (d:Person {name: 'Diana', age: 28}),
       (a)-[:KNOWS]->(b),
       (a)-[:KNOWS]->(c),
       (b)-[:KNOWS]->(d),
       (c)-[:KNOWS]->(d)

# %% [markdown]
# ## Query Data

# %%
# List all people
%%cypher
MATCH (p:Person)
RETURN p.name AS name, p.age AS age
ORDER BY p.age

# %%
# Find who knows whom
%%cypher
MATCH (a:Person)-[:KNOWS]->(b:Person)
RETURN a.name AS person, b.name AS knows

# %%
# Friends of friends
%%cypher
MATCH (a:Person {name: 'Alice'})-[:KNOWS]->()-[:KNOWS]->(fof:Person)
WHERE NOT (a)-[:KNOWS]->(fof) AND a <> fof
RETURN DISTINCT fof.name AS friend_of_friend

# %%
# Count relationships
%%cypher
MATCH (p:Person)-[r:KNOWS]->()
RETURN p.name AS person, count(r) AS knows_count
ORDER BY knows_count DESC

# %% [markdown]
# ## Clean Up

# %%
%%cypher
MATCH (n) DETACH DELETE n
