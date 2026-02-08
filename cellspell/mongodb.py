"""Convenience module for: %load_ext cellspell.mongodb"""

from .spells.mongodb import load_ipython_extension, unload_ipython_extension

__all__ = ["load_ipython_extension", "unload_ipython_extension"]
