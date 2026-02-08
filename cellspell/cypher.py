"""Convenience module for: %load_ext cellspell.cypher"""

from .spells.cypher import load_ipython_extension, unload_ipython_extension

__all__ = ["load_ipython_extension", "unload_ipython_extension"]
