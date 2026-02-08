"""Convenience module for: %load_ext cellspell.xpath"""

from .spells.xpath import load_ipython_extension, unload_ipython_extension

__all__ = ["load_ipython_extension", "unload_ipython_extension"]
