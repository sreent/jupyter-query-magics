"""cellspell.spells.gql — ISO GQL cell magic (planned).

Will support:
    %%gql
    MATCH (p:Person)-[:KNOWS]->(q:Person)
    RETURN p.name, q.name

Backends:
    - GraphLite (Rust, via REST API)
"""

# TODO: Implement GQL spell


def load_ipython_extension(ipython):
    raise NotImplementedError(
        "GQL spell is not yet implemented. Coming soon!\n"
        "Track progress at: https://github.com/yourusername/cellspell"
    )


def unload_ipython_extension(ipython):
    pass
