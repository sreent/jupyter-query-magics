"""cellspell — A spellbook of Jupyter cell magics for query languages.

Available spells:
    %%xpath    — XPath queries via xmllint
    %%cypher   — Cypher queries via Neo4j / KùzuDB  (planned)
    %%sparql   — SPARQL queries via RDFLib           (planned)
    %%mongodb  — MongoDB queries via PyMongo          (planned)
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
    from .spells.xpath import load_ipython_extension as load_xpath

    load_xpath(ipython)

    # Future spells — uncomment as they become available:
    # from .spells.cypher import load_ipython_extension as load_cypher
    # from .spells.sparql import load_ipython_extension as load_sparql
    # from .spells.mongodb import load_ipython_extension as load_mongodb

    print(f"🔮 cellspell v{__version__} — spellbook loaded")


def unload_ipython_extension(ipython):
    """Unload all cellspell magics."""
    pass
