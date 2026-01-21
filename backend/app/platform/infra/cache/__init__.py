"""
Platform Cache Module.
Caching interfaces and implementations.
"""

from .cache import CacheBackend, PlatformCache

__all__ = [
    "CacheBackend",
    "PlatformCache",
]
