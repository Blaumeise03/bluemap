"""
This module provides tools for rendering influence maps for games like Eve Online/Echoes. The rendering is implemented
in C++ and Cython to achieve high performance, while still maintaining a simple and flexible Python API. Please note
that the API is still in development and might change until the first stable release.

.. include:: ../README.md
   :start-line: 2

# Core classes
"""

__all__ = ['SovMap', 'ColumnWorker', 'SolarSystem', 'Region', 'Owner', 'MapOwnerLabel', 'OwnerImage', 'stream', 'table']

from ._map import *