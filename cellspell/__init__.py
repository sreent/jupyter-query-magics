"""cellspell — A spellbook of Jupyter cell magics for query languages.

Available spells:
    %%xpath    — XPath queries via xmllint
    %%cypher   — Cypher queries via Neo4j
    %%sparql   — SPARQL queries via RDFLib / remote endpoints
    %%mongodb  — MongoDB queries via PyMongo
    %%gql      — ISO GQL queries                      (planned)

Usage:
    %load_ext cellspell          # Load all available spells
    %load_ext cellspell.xpath    # Load only XPath spell
"""

__version__ = "0.1.0"


def load_ipython_extension(ipython):
    """Load all available cellspell magics.

    Usage in Jupyter:
        %load_ext cellspell
    """
    loaded = []

    # XPath — requires xmllint (system tool, no pip dependency)
    try:
        from .spells.xpath import load_ipython_extension as load_xpath

        load_xpath(ipython)
        loaded.append("xpath")
    except Exception:
        pass

    # Cypher — requires neo4j pip package
    try:
        from .spells.cypher import load_ipython_extension as load_cypher

        load_cypher(ipython)
        loaded.append("cypher")
    except Exception:
        pass

    # SPARQL — rdflib optional (remote endpoints work without it)
    try:
        from .spells.sparql import load_ipython_extension as load_sparql

        load_sparql(ipython)
        loaded.append("sparql")
    except Exception:
        pass

    # MongoDB — requires pymongo pip package
    try:
        from .spells.mongodb import load_ipython_extension as load_mongodb

        load_mongodb(ipython)
        loaded.append("mongodb")
    except Exception:
        pass

    if loaded:
        print(f"🔮 cellspell v{__version__} — loaded: {', '.join(loaded)}")
    else:
        print(
            f"🔮 cellspell v{__version__} — no spells loaded.\n"
            "Install backends: pip install cellspell[all]"
        )


def unload_ipython_extension(ipython):
    """Unload all cellspell magics."""
    pass
