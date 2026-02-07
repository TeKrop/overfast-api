"""
Cache manager module - DEPRECATED, moved to app/adapters/cache/valkey_cache.py

This module is kept for backward compatibility during the migration to v4.
Import from app.adapters.cache instead.
"""

from app.adapters.cache import CacheManager

__all__ = ["CacheManager"]

