"""cellspell.spells.sparql — SPARQL cell magic (planned).

Will support:
    %%sparql                                   Query default graph
    %%sparql https://dbpedia.org/sparql        Query remote endpoint
    %%sparql --local                           Query local RDFLib graph

Backends:
    - RDFLib (local in-memory)
    - Oxigraph (local embedded)
    - Remote SPARQL endpoints
"""

# TODO: Implement SPARQL spell


def load_ipython_extension(ipython):
    raise NotImplementedError(
        "SPARQL spell is not yet implemented. Coming soon!\n"
        "Track progress at: https://github.com/yourusername/cellspell"
    )


def unload_ipython_extension(ipython):
    pass
