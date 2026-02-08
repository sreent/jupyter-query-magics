"""cellspell.spells.cypher — Cypher cell magic (planned).

Will support:
    %%cypher                      Query default connection
    %%cypher bolt://host:7687     Query specific Neo4j instance
    %%cypher kuzu://./mydb        Query KùzuDB

Backends:
    - Neo4j (via neo4j Python driver)
    - KùzuDB (via kuzu)
"""

# TODO: Implement Cypher spell


def load_ipython_extension(ipython):
    raise NotImplementedError(
        "Cypher spell is not yet implemented. Coming soon!\n"
        "Track progress at: https://github.com/yourusername/cellspell"
    )


def unload_ipython_extension(ipython):
    pass
